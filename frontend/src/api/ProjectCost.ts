import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import { analytics } from "../shared/analytics.ts";
import type { CostItem } from "../shared/models/Project.ts";

export interface ProjectCostRequest {
  idToken: string;
  operation?: "install" | "uninstall";
  appIds?: string[];
}

export interface ProjectCostResponse {
  current: CostItem[];
  pending?: CostItem[];
}

export async function projectCost({
  idToken,
  operation,
  appIds,
}: ProjectCostRequest): Promise<ProjectCostResponse> {
  let response: AxiosResponse;
  try {
    response = await axios.post(
      "/api/cost",
      {
        operation,
        app_ids: appIds,
      },
      {
        headers: {
          ...(idToken && { Authorization: `Bearer ${idToken}` }),
        },
      },
    );

    return response.data as ProjectCostResponse;
  } catch (e: any) {
    const error = new ApiError({
      errorId: "ProjectCost",
      message: "An error occurred while projecting project cost.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  } finally {
    analytics.track("ProjectCost", {
      status: response.status,
    });
  }
}
