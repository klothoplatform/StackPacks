import type { AxiosResponse } from "axios";
import axios from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import type { Stack } from "../shared/models/Stack.ts";
import { analytics } from "../shared/analytics.ts";

export interface CreateStackRequest {
  idToken: string;
  stack: Partial<Stack>;
}

export interface CreateStackResponse {
  stack: Stack;
  policy: string;
}

export async function createStack(
  request: CreateStackRequest,
): Promise<CreateStackResponse> {
  let response: AxiosResponse;
  try {
    response = await axios.post(
      "/api/stack",
      { ...request.stack, status: "new" },
      {
        headers: {
          ...(request.idToken && {
            Authorization: `Bearer ${request.idToken}`,
          }),
        },
      },
    );
  } catch (e: any) {
    const error = new ApiError({
      errorId: "CreateStack",
      message: "An error occurred while creating your stack.",
      status: e.status,
      statusText: e.message,
      url: e.request?.url,
      cause: e,
    });
    trackError(error);
    throw error;
  }

  analytics.track("CreateStack", {
    status: response.status,
    data: {
      stackPacks: Object.keys(request.stack.configuration),
    },
  });
  return response.data as CreateStackResponse;
}
