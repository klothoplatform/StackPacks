import type { FC } from "react";
import React from "react";
import useApplicationStore from "../store/ApplicationStore.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { UIError } from "../../shared/errors.ts";
import { Card } from "flowbite-react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import { useNavigate } from "react-router-dom";

export const YourStackPane: FC = () => {
  const { userStack, addError, getUserStack } = useApplicationStore();
  const navigate = useNavigate();

  useDocumentTitle("StackPacks - Your Stack");
  useEffectOnMount(() => {
    (async () => {
      try {
        const stack = await getUserStack();
        if (!stack) {
          navigate("/onboarding");
        }
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
            <p>{userStack.region}</p>
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
