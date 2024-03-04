import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.scss";
import App from "./App";
import { env } from "./shared/environment";
import FlowbiteWrapper from "./components/FlowbiteWrapper.tsx";

const container = document.getElementById("root");

if (!container) {
  throw new Error("React root element doesn't exist!");
}

function enableSessionRewind(args: {
  apiKey: string;
  startRecording: boolean;
}) {
  (window as any).SessionRewindConfig = args;
  const f = document.createElement("script") as any;
  f.async = 1;
  f.crossOrigin = "anonymous";
  f.src = "https://rec.sessionrewind.com/srloader.js";
  const g = document.getElementsByTagName("head")[0];
  g.insertBefore(f, g.firstChild);
}

if (env.sessionRewind.enabled) {
  enableSessionRewind({
    apiKey: env.sessionRewind.apiKey,
    startRecording: true,
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
