import type { AxiosResponse } from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import type { Stack } from "../shared/models/Stack.ts";
import { client } from "../shared/axios.ts";
import { analytics } from "../shared/analytics.ts";

export async function getStack(idToken: string): Promise<Stack> {
  let response: AxiosResponse;
  try {
    response = await client.get("/api/stack", {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "GetStack",
      message: "An error occurred while getting your stack.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("GetStack", {
    status: response.status,
  });
  return parseStack(response.data);
}

// TODO: implement stack parser
function parseStack(data: any): Stack {
  return data;
}
