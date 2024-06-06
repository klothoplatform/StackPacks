import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.scss";
import App from "./App";
import { env } from "./shared/environment";
import FlowbiteWrapper from "./components/FlowbiteWrapper.tsx";

interface SessionRewindConfig {
  apiKey: string;
  startRecording: boolean;
  createNewSession?: boolean;
  onLoad?: () => void;
}

const container = document.getElementById("root");

if (!container) {
  throw new Error("React root element doesn't exist!");
}

if (env.sessionRewind.enabled) {
  (function (config: SessionRewindConfig) {
    const w = window as any;

    w.SessionRewindConfig = config;

    const script = document.createElement("script");
    script.async = true;
    script.crossOrigin = "anonymous";
    script.src = "https://rec.sessionrewind.com/srloader.js";

    const head = document.getElementsByTagName("head")[0];
    head.insertBefore(script, head.firstChild);
  })({
    apiKey: env.sessionRewind.apiKey,
    startRecording: true,
    onLoad: () => {
      (window as any).sessionRewind.setSessionInfo({
        Environment: env.environment,
        Product: "StackSnap",
      });
    },
  });
}

const root = createRoot(container);
root.render(
  <StrictMode>
    <FlowbiteWrapper>
      <App />
    </FlowbiteWrapper>
  </StrictMode>,
);
