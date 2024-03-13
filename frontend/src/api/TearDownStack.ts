import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { analytics } from "../shared/analytics.ts";

export async function tearDownStack(idToken: string): Promise<string> {
  let response: AxiosResponse;
  try {
    response = await axios.post("/api/tear_down", {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });

    return response.data.deployment_id;
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
  } finally {
    analytics.track("TearDownStack", {
      status: response.status,
    });
  }
}
