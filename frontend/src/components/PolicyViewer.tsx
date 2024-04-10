import { Container } from "./Container.tsx";
import { CopyToClipboardButton } from "./CopyToClipboardButton.tsx";
import React from "react";

export function PolicyViewer(props: {
  text: string | undefined;
  color: "light" | "dark" | "auto";
}) {
  return (
    <Container className={"relative p-0"}>
      <CopyToClipboardButton
        text={props.text}
        color={props.color}
        className={"absolute right-0 top-0 mr-4 mt-2 p-0"}
      />
      <div
        className={
          "max-h-80 w-full overflow-y-auto whitespace-pre-wrap rounded-lg bg-white p-4 font-mono text-xs text-green-700 dark:bg-gray-800 dark:text-green-200"
        }
      >
        <code>{props.text}</code>
      </div>
    </Container>
  );
}
