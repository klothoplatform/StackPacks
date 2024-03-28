import type {
  WorkflowRunSummary,
  WorkflowType,
} from "../shared/models/Workflow.ts";
import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors.ts";
import { trackError } from "../pages/store/ErrorStore.ts";

export interface GetWorkflowRunsRequest {
  idToken: string;
  workflowType?: WorkflowType;
  appId?: string;
}

export async function getWorkflowRuns({
  idToken,
  workflowType,
  appId,
}: GetWorkflowRunsRequest): Promise<WorkflowRunSummary[]> {
  const appRunsUrl = `/api/project/apps/${appId}/workflows/${workflowType}/runs`;
  const projectRunsUrl = `/api/project/workflows/${workflowType}/runs`;
  const url = appId ? appRunsUrl : projectRunsUrl;

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
      errorId: "GetWorkflowRunsError",
    });
    trackError(apiError);
    throw apiError;
  }

  return response.data;
}
