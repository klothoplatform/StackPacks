import type { AxiosResponse } from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { client } from "../shared/axios.ts";
import { analytics } from "../shared/analytics.ts";
import type { StackPack } from "../shared/models/StackPack.ts";
import type { RawProperty } from "../shared/configuration-properties.ts";
import { parseProperty } from "../shared/configuration-properties.ts";

// const mockApps: StackPack[] = Array.from({ length: 10 }, (_, index) => ({
//   name: `App ${index + 1}`,
//   description: `This is App ${index + 1}`,
//   tags: [],
//   version: "1.0.0",
//   configuration: {},
//   alternatives: [],
// }));

export async function getStackPacks(
  idToken: string,
): Promise<Map<string, StackPack>> {
  // return parseStackPacks(mockApps);

  // todo: call backend

  let response: AxiosResponse;
  try {
    response = await client.get("/api/stackpacks", {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "GetStackPack",
      message: "An error occurred while getting the StackPack list.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("GetStackPacks", {
    status: response.status,
  });
  return parseStackPacks(response.data);
}

// TODO: implement stackpack parser
function parseStackPacks(data: any): Map<string, StackPack> {
  console.log(data);
  const packs = new Map<string, StackPack>();
  Object.entries(data).forEach(([name, pack]: [string, StackPack]) => {
    pack.configuration = Object.fromEntries(
      Object.values(pack.configuration).map((v) => [
        v.name,
        parseProperty(v as any as RawProperty),
      ]),
    );
    packs.set(name, pack);
  });
  return packs;
}
