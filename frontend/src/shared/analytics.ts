import { AnalyticsBrowser } from "@segment/analytics-next";
import { env } from "./environment";

export const analytics = AnalyticsBrowser.load(
  {
    writeKey: env.analytics.writeKey,
    cdnURL: "https://analytics.infracopilot.io",
  },
  {
    integrations: {
      "Segment.io": {
        apiHost: "api.analytics.infracopilot.io/v1",
      },
    },
  },
);
