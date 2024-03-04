import type { AxiosResponse } from "axios";
import { ApiError } from "../shared/errors";
import { trackError } from "../pages/store/ErrorStore";
import type { Stack } from "../shared/models/Stack.ts";
import { client } from "../shared/axios.ts";
import { analytics } from "../shared/analytics.ts";

export interface UpdateStackRequest {
  idToken: string;
  stack: Partial<Stack>;
}

export async function updateStack(request: UpdateStackRequest): Promise<Stack> {
  let response: AxiosResponse;
  try {
    response = await client.patch("/api/stack", request.stack, {
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
      stackPacks: Object.keys(request.stack.configuration),
    },
  });
  return parseStack(response.data);
}

// TODO: implement stack parser
function parseStack(data: any): Stack {
  return data;
}
