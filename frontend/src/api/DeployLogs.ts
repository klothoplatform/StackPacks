import type { EventSourceMessage } from "@microsoft/fetch-event-source";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { ApiError } from "../shared/errors.ts";

export type LogStreamListener = (message: EventSourceMessage) => void;

export enum DeployLogEventType {
  LogLine = "log-line",
  Done = "done",
}

class RetryableError extends Error {}
export class AbortError extends Error {}

export interface DeployLogSubscriptionRequest {
  idToken: string;
  deploymentId: string;
  appId: string;
  listener: LogStreamListener;
  controller?: AbortController;
}

export async function subscribeToLogStream({
  deploymentId,
  appId,
  idToken,
  listener,
  controller,
}: DeployLogSubscriptionRequest) {
  controller = controller || new AbortController();
  await fetchEventSource(
    `/api/stack/${appId}/deployment/${deploymentId}/logs`,
    {
      headers: {
        ...(idToken && { Authorization: `Bearer ${idToken}` }),
      },
      signal: controller.signal,
      async onopen(response) {
        if (response.ok) {
          return; // everything's good
        } else if (
          response.status >= 400 &&
          response.status < 500 &&
          response.status !== 429
        ) {
          // client-side errors are usually non-retryable:
          throw new ApiError({
            errorId: "LOG_STREAM_ERROR",
            message: await response.text(),
            status: response.status,
            statusText: response.statusText,
            url: response.url,
          });
        } else {
          throw new RetryableError();
        }
      },
      onmessage: (message) => {
        if (controller.signal.aborted) {
          throw new AbortError();
        }
        listener(message);
      },
      onclose() {
        if (controller.signal.aborted) {
          return; // we aborted the request, no need to retry
        }
        throw new RetryableError();
      },
      onerror(err) {
        if (controller.signal.aborted) {
          throw new AbortError();
        }
        if (err instanceof ApiError || err instanceof AbortError) {
          throw err;
        } else {
          return 30000; // retry after 3 seconds
        }
      },
    },
  );
}
