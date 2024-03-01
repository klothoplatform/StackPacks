import type { AxiosResponse } from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { client } from "../shared/axios.ts";
import { analytics } from "../shared/analytics.ts";

export async function installStack(idToken: string) {
  let response: AxiosResponse;
  try {
    response = await client.post("/api/install", {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "InstallStack",
      message: "An error occurred while installing your stack.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("InstallStack", {
    status: response.status,
  });
}
