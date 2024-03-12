import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { analytics } from "../shared/analytics.ts";

export interface TearDownAppRequest {
  idToken: string;
  appId: string;
}

export async function tearDownApp({
  idToken,
  appId,
}: TearDownAppRequest): Promise<string> {
  let response: AxiosResponse;
  try {
    response = await axios.post(`/api/tear_down/${appId}`, {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "TearDownApp",
      message: "An error occurred while tearing down your app.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("TearDownApp", {
    status: response.status,
    appId: appId,
  });

  return response.data;
}
