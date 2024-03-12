import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { analytics } from "../shared/analytics.ts";

export interface InstallAppRequest {
  appId: string;
  idToken: string;
}

export async function installApp({
  appId,
  idToken,
}: InstallAppRequest): Promise<string> {
  let response: AxiosResponse;
  try {
    response = await axios.post(`/api/install/${appId}`, {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "InstallApp",
      message: "An error occurred while installing your app.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("InstallApp", {
    status: response.status,
    appId: appId,
  });

  return response.data;
}
