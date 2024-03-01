import type { AxiosResponse } from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { client } from "../shared/axios.ts";
import { analytics } from "../shared/analytics.ts";
import type { StackPack } from "../shared/models/StackPack.ts";

export async function getStackPacks(
  idToken: string,
): Promise<Map<string, StackPack>> {
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
  return data;
}
