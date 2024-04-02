import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { analytics } from "../shared/analytics.ts";
import type { WorkflowRunSummary } from "../shared/models/Workflow.ts";

export interface UninstallAppRequest {
  idToken: string;
  appId: string;
}

export async function uninstallApp({
  idToken,
  appId,
}: UninstallAppRequest): Promise<WorkflowRunSummary> {
  let response: AxiosResponse;
  try {
    response = await axios.post(
      `/api/project/apps/${appId}/workflows/uninstall`,
      undefined,
      {
        headers: {
          ...(idToken && { Authorization: `Bearer ${idToken}` }),
        },
      },
    );
  } catch (e: any) {
    const error = new ApiError({
      errorId: "UninstallApp",
      message: "An error occurred while tearing down your app.",
      status: e.status,
      statusText: e.message,
      path: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("UninstallApp", {
    status: response.status,
    appId: appId,
  });

  return response.data as WorkflowRunSummary;
}
