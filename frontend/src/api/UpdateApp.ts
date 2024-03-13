import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { analytics } from "../shared/analytics.ts";
import type { UserStack } from "../shared/models/UserStack.ts";
import { parseStack } from "../shared/models/UserStack.ts";

export interface UpdateAppRequest {
  idToken: string;
  appId: string;
  configuration: Record<string, any>;
}

export interface UpdateAppResponse {
  stack: UserStack;
  policy: string;
}

export async function updateApp({
  appId,
  configuration,
  idToken,
}: UpdateAppRequest): Promise<UpdateAppResponse> {
  let response: AxiosResponse;
  try {
    response = await axios.patch(`/api/stack/${appId}`, configuration, {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "UpdateApp",
      message: "An error occurred while creating your app.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("UpdateApp", {
    status: response.status,
    data: {
      appId,
      configurationCount: Object.keys(configuration ?? {}).length,
    },
  });
  return {
    stack: parseStack(response.data.stack),
    policy: response.data.policy,
  };
}
