import type { AxiosResponse } from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import type { Stack } from "../shared/models/Stack.ts";
import { client } from "../shared/axios.ts";
import { analytics } from "../shared/analytics.ts";

export interface CreateStackRequest {
  idToken: string;
  stack: Stack;
}

export async function createStack(request: CreateStackRequest): Promise<Stack> {
  let response: AxiosResponse;
  try {
    response = await client.post("/api/stack", request.stack, {
      headers: {
        ...(request.idToken && { Authorization: `Bearer ${request.idToken}` }),
      },
    });
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
      stackPacks: Object.keys(request.stack.stackPacks),
    },
  });
  return parseStack(response.data);
}

// TODO: implement stack parser
function parseStack(data: any): Stack {
  return data;
}
