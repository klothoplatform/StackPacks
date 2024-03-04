import type { FC } from "react";
import React from "react";
import useApplicationStore from "../store/ApplicationStore.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { UIError } from "../../shared/errors.ts";
import { Card } from "flowbite-react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";

export const YourStackPane: FC = () => {
  const { userStack, addError, loadUserStack } = useApplicationStore();
  useDocumentTitle("StackPacks - Your Stack");
  useEffectOnMount(() => {
    (async () => {
      try {
        await loadUserStack();
      } catch (e) {
        addError(
          new UIError({
            message: "Failed to load user stack",
            cause: e,
          }),
        );
      }
    })();
  });

  return (
    <div className="flex size-full flex-col gap-6">
      <h3 className={"font-md text-lg"}>Your Stack</h3>
      {userStack && (
        <div className="flex size-full flex-col gap-2">
          <Card className="flex h-fit w-full flex-col p-4">
            <h4 className={"font-md text-md"}>Status: {userStack.status}</h4>
            <p>{userStack.statusReason}</p>
            <div className={"h-fit w-full p-2"}>
              <h4 className={"font-md text-md"}>StackPacks</h4>
              {Object.keys(userStack.configuration).map((app, index) => {
                return (
                  <div key={index} className={"flex size-full flex-col gap-2"}>
                    <div className={"font-md text-md"}>{app}</div>
                    <code>
                      {JSON.stringify(userStack.configuration[app] ?? {})}
                    </code>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};
