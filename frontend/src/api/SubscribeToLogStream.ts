import type { EventSourceMessage } from "@microsoft/fetch-event-source";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { ApiError } from "../shared/errors.ts";
import type { WorkflowType } from "../shared/models/Workflow.ts";

export type LogStreamListener = (message: EventSourceMessage) => void;

export enum DeployLogEventType {
  LogLine = "log-line",
  Done = "done",
}

class RetryableError extends Error {}

export class AbortError extends Error {}

export interface LogSubscriptionRequest {
  idToken: string;
  workflowType: WorkflowType;
  targetedAppId?: string;
  runNumber: number;
  jobNumber: number;
  listener: LogStreamListener;
  controller?: AbortController;
}

export async function subscribeToLogStream({
  workflowType,
  runNumber,
  targetedAppId,
  jobNumber,
  idToken,
  listener,
  controller,
}: LogSubscriptionRequest) {
  controller = controller || new AbortController();

  const appLogsUrl = `/api/project/apps/${targetedAppId}/workflows/${workflowType}/runs/${runNumber}/jobs/${jobNumber}/logs`;
  const projectLogsUrl = `/api/project/workflows/${workflowType}/runs/${runNumber}/jobs/${jobNumber}/logs`;
  const url = targetedAppId ? appLogsUrl : projectLogsUrl;
  await fetchEventSource(url, {
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
  });
}
