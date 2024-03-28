import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { analytics } from "../shared/analytics.ts";
import type { Project } from "../shared/models/Project.ts";
import { parseProject } from "../shared/models/Project.ts";

export interface RemoveAppRequest {
  idToken: string;
  appId: string;
}

export interface RemoveAppResponse {
  stack: Project;
  policy: string;
}

export async function removeApp({
  appId,
  idToken,
}: RemoveAppRequest): Promise<RemoveAppResponse> {
  let response: AxiosResponse;
  try {
    response = await axios.delete(`/api/project/${appId}`, {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "RemoveApp",
      message: "An error occurred while creating your app.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("RemoveApp", {
    status: response.status,
    data: {
      appId,
    },
  });
  return {
    stack: parseProject(response.data.stack),
    policy: response.data.policy,
  };
}
