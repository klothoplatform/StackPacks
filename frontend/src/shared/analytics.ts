import { env } from "./environment";
import { RudderAnalytics } from "@rudderstack/analytics-js";

export const analytics = new RudderAnalytics();
analytics.load(env.analytics.writeKey, env.analytics.dataplaneUrl, {
  storage: {
    encryption: {
      version: "v3",
    },
  },
});
