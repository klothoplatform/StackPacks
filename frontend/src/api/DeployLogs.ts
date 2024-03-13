// import { ApiError } from "../shared/errors.ts";
// import { trackError } from "../pages/store/ErrorStore.ts";
// import { analytics } from "../shared/analytics.ts";
import { NativeEventSource, EventSourcePolyfill } from "event-source-polyfill";
const EventSource = NativeEventSource || EventSourcePolyfill;

export function deployLogs(
  idToken: string,
  deploy_id: string,
  app_id,
): EventSource {
  return new EventSource(`/api/logs/${deploy_id}/${app_id}`, {
    Headers: idToken && { Authorization: `Bearer ${idToken}` },
  });
}
