import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors.ts";
import { trackError } from "../pages/store/ErrorStore.ts";
import type { WorkflowRun, WorkflowType } from "../shared/models/Workflow.ts";

export interface GetWorkflowRunRequest {
  idToken: string;
  workflowType?: WorkflowType;
  appId?: string;
  runNumber?: number | "latest";
}

export async function getWorkflowRun({
  idToken,
  workflowType,
  appId,
  runNumber,
}: GetWorkflowRunRequest): Promise<WorkflowRun> {
  const appRunUrl = `/api/project/apps/${appId}/workflows/${workflowType}/runs/${runNumber}`;
  const projectRunUrl = `/api/project/workflows/${workflowType}/runs/${runNumber}`;
  const url = appId ? appRunUrl : projectRunUrl;

  let response: AxiosResponse;
  try {
    response = await axios.get(url, {
      headers: idToken && { Authorization: `Bearer ${idToken}` },
    });
  } catch (error) {
    const apiError = new ApiError({
      status: error.response.status,
      statusText: error.response.statusText,
      message: error.response.data.message,
      cause: error,
      errorId: "GetWorkflowRunError",
    });
    trackError(apiError);
    throw apiError;
  }

  return response.data;
}
