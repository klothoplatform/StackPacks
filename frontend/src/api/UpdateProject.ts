import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import type { ProjectModification, Project } from "../shared/models/Project.ts";
import { parseProject } from "../shared/models/Project.ts";
import { analytics } from "../shared/analytics.ts";

export interface UpdateProjectRequest {
  idToken: string;
  stack: ProjectModification;
}

export interface UpdateProjectResponse {
  stack: Project;
  policy: string;
}

export async function updateProject(
  request: UpdateProjectRequest,
): Promise<UpdateProjectResponse> {
  let response: AxiosResponse;
  try {
    response = await axios.patch("/api/project", request.stack, {
      headers: {
        ...(request.idToken && { Authorization: `Bearer ${request.idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "UpdateProject",
      message: "An error occurred while updating your project",
      status: e.status,
      statusText: e.message,
      path: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("UpdateProject", {
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
