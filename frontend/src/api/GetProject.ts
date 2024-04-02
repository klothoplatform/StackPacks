import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import type { Project } from "../shared/models/Project.ts";
import { parseProject } from "../shared/models/Project.ts";
import { analytics } from "../shared/analytics.ts";

export async function getProject(idToken: string): Promise<Project> {
  let response: AxiosResponse;
  try {
    response = await axios.get("/api/project", {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
    });
  } catch (e: any) {
    if (e.response?.status === 404) {
      analytics.track("GetProject", {
        status: e.response.status,
      });
      return undefined;
    }

    const error = new ApiError({
      errorId: "GetProject",
      message: "An error occurred while getting your project.",
      status: e.response?.status,
      statusText: e.response?.message || e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("GetProject", {
    status: response.status,
  });
  return parseProject(response.data);
}
