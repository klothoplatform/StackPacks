import type { AxiosResponse } from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { client } from "../shared/axios.ts";
import { analytics } from "../shared/analytics.ts";

export async function tearDownStack(idToken: string) {
  let response: AxiosResponse;
  try {
    response = await client.post("/api/tear_down", {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "TearDownStack",
      message: "An error occurred while tearing down your stack.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("TearDownStack", {
    status: response.status,
  });
}
