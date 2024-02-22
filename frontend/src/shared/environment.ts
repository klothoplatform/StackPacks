/*
env centralizes all environment settings for the application.

This includes environment variables, but also settings that are derived from environment variables.

Avoid using environment variables directly in the application.
Instead, use env to keep it clean.
 */

type typedMetaEnv = {
    [key: string]: string;
} & Pick<ImportMetaEnv, "BASE_URL" | "MODE" | "DEV" | "PROD" | "SSR">

const viteEnv: typedMetaEnv = import.meta.env as typedMetaEnv;

export const env: Environment = {
  environment: viteEnv.VITE_ENVIRONMENT ?? import.meta.env.PROD ? "production" : "development",
  debug: new Set(
    (viteEnv.VITE_DEBUG ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0),
  ),
  sessionRewind: {
    enabled:
      viteEnv.VITE_SESSIONREWIND_ENABLED?.toLowerCase() === "true",
    apiKey: "66s8iL8YHi3iOXBqda2YSA4zLJeNyCZ8TazdUBR9",
  },
  auth0: {
    domain: viteEnv.VITE_AUTH0_DOMAIN,
    clientId: viteEnv.VITE_AUTH0_CLIENT_ID,
    callbackUrl: viteEnv.VITE_AUTH0_CALLBACK_URL,
    logoutUrl: viteEnv.VITE_AUTH0_LOGOUT_URL,
  },
  analytics: {
    writeKey: "GKCsKtwCdTQO75tRzBPKAw82xVPYPqEz",
    trackErrors:
      viteEnv.VITE_ANALYTICS_TRACK_ERRORS?.toLowerCase() !== "false",
  },
};

export interface Environment {
  debug: Set<string>;
  sessionRewind: {
    enabled: boolean;
    apiKey: string;
  };
  auth0: {
    domain?: string;
    clientId?: string;
    callbackUrl?: string;
    logoutUrl?: string;
  };
  analytics: {
    writeKey: string;
    trackErrors: boolean;
  };
  environment: string;
}
