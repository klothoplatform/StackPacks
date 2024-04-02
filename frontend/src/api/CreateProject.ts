import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import type { ProjectModification, Project } from "../shared/models/Project.ts";
import { parseProject } from "../shared/models/Project.ts";
import { analytics } from "../shared/analytics.ts";

export interface CreateStackRequest {
  idToken: string;
  stack: ProjectModification;
}

export interface CreateStackResponse {
  stack: Project;
  policy: string;
}

export async function createProject(
  request: CreateStackRequest,
): Promise<CreateStackResponse> {
  let response: AxiosResponse;
  try {
    response = await axios.post("/api/project", request.stack, {
      headers: {
        ...(request.idToken && {
          Authorization: `Bearer ${request.idToken}`,
        }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "CreateStack",
      message: "An error occurred while creating your stack.",
      status: e.status,
      statusText: e.message,
      path: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("CreateStack", {
    status: response.status,
    data: {
      stackPacks: Object.keys(request.stack?.configuration || {}),
    },
  });
  return {
    stack: parseProject(response.data.stack),
    policy: response.data.policy,
  };
}
