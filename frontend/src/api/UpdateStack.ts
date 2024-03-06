import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import type {
  StackModification,
  UserStack,
} from "../shared/models/UserStack.ts";
import { analytics } from "../shared/analytics.ts";

export interface UpdateStackRequest {
  idToken: string;
  stack: StackModification;
}

export interface UpdateStackResponse {
  stack: UserStack;
  policy: string;
}

export async function updateStack(
  request: UpdateStackRequest,
): Promise<UpdateStackResponse> {
  let response: AxiosResponse;
  try {
    response = await axios.patch("/api/stack", request.stack, {
      headers: {
        ...(request.idToken && { Authorization: `Bearer ${request.idToken}` }),
      },
    });
  } catch (e: any) {
    const error = new ApiError({
      errorId: "UpdateStack",
      message: "An error occurred while creating your stack.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("UpdateStack", {
    status: response.status,
    data: {
      stackPacks: Object.keys(request.stack?.configuration || {}),
    },
  });
  return response.data as UpdateStackResponse;
}
