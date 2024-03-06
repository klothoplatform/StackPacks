import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { analytics } from "../shared/analytics.ts";
import type { StackPack } from "../shared/models/StackPack.ts";
import type { RawProperty } from "../shared/configuration-properties.ts";
import { parseProperty } from "../shared/configuration-properties.ts";

export async function getStackPacks(
  idToken: string,
): Promise<Map<string, StackPack>> {
  let response: AxiosResponse;
  try {
    response = await axios.get("/api/stackpacks", {
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

function parseStackPacks(data: any): Map<string, StackPack> {
  console.log(data);
  const packs = new Map<string, StackPack>();
  Object.entries(data).forEach(([name, pack]: [string, StackPack]) => {
    pack.configuration = Object.fromEntries(
      Object.entries(pack.configuration).map(([id, property]) => [
        id,
        parseProperty({ ...property, id } as any as RawProperty),
      ]),
    );
    packs.set(name, pack);
  });
  return packs;
}
