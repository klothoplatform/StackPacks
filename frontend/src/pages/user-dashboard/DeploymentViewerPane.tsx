import React, { type FC, useEffect, useState } from "react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import { useNavigate, useParams } from "react-router-dom";
import useApplicationStore from "../store/ApplicationStore.ts";
import type { CustomFlowbiteTheme } from "flowbite-react";
import { Card, Tabs } from "flowbite-react";
import { ErrorBoundary } from "react-error-boundary";
import { FallbackRenderer } from "../../components/FallbackRenderer.tsx";
import { trackError } from "../store/ErrorStore.ts";
import { UIError } from "../../shared/errors.ts";
import Ansi from "ansi-to-react-18";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import type { EventSourceMessage } from "@microsoft/fetch-event-source";
import { AbortError, DeployLogEventType } from "../../api/DeployLogs.ts";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import "./ansi.scss";

const tabTheme: CustomFlowbiteTheme["tabs"] = {
  base: "flex flex-col gap-2 size-full",
  tabitemcontainer: {
    base: "size-full overflow-hidden",
  },
  tabpanel: "py-3 size-full overflow-hidden",
  tablist: {
    styles: {
      underline: "flex-no-wrap -mb-px",
    },
    tabitem: {
      base: "text-primary-500 dark:text-primary-300 flex items-center justify-center p-2 text-sm font-medium first:ml-0 disabled:cursor-not-allowed disabled:text-gray-400 disabled:dark:text-gray-500 focus:outline-none",
      styles: {
        underline: {
          base: "",
          active: {
            on: "text-primary-600 border-b-2 border-primary-600 active dark:border-primary-500",
            off: "border-b-2 border-transparent hover:border-primary-300 hover:text-primary-600 dark:text-primary-400 dark:hover:text-primary-300",
          },
        },
      },
    },
  },
};

export const DeploymentViewerPane: FC = () => {
  useDocumentTitle("StackPacks - Log Viewer");
  const { deployId, appId } = useParams();

  const navigate = useNavigate();

  useEffectOnMount(() => {
    if (!deployId) {
      navigate(`..`);
    }
  });

  const { userStack } = useApplicationStore();
  const [applications, setApplications] = useState([
    "common",
    ...Object.keys(userStack?.stack_packs ?? {}),
  ]);

  useEffect(() => {
    setApplications(["common", ...Object.keys(userStack?.stack_packs ?? {})]);
  }, [userStack]);

  useEffect(() => {
    if (!appId && applications.length > 0 && applications[0] !== undefined) {
      navigate(`/user/dashboard/deploy/${deployId}/app/${applications[0]}`);
    }
  }, [appId, deployId, applications, navigate]);

  const changeTab = (tab: number) => {
    const app = applications[tab];
    if (app !== appId && app !== undefined) {
      navigate(`/user/dashboard/deploy/${deployId}/app/${app}`);
    }
  };

  return (
    <ErrorBoundary
      fallbackRender={FallbackRenderer}
      onError={(error, info) => {
        trackError(
          new UIError({
            message: "uncaught error in DeploymentViewerPane",
            errorId: "DeploymentViewerPane:ErrorBoundary",
            cause: error,
            data: {
              info,
            },
          }),
        );
      }}
    >
      <Tabs
        theme={tabTheme}
        // eslint-disable-next-line react/style-prop-object
        style="underline"
        onActiveTabChange={changeTab}
      >
        {applications.map((app, index) => {
          if (app !== appId) {
            return <Tabs.Item key={index} title={app} />;
          } else {
            return (
              <Tabs.Item key={index} active title={app}>
                <LogPane key={app} appId={app} deployId={deployId} />
              </Tabs.Item>
            );
          }
        })}
      </Tabs>
    </ErrorBoundary>
  );
};

const LogPane: FC<{
  appId: string;
  deployId: string;
}> = ({ appId, deployId }) => {
  const logPaneRef = React.useRef<HTMLDivElement>(null);
  const { subscribeToLogStream } = useApplicationStore();
  const [done, setDone] = useState(false);

  const [log, setLog] = useState([] as string[]);
  const [hasUserScrolled, setHasUserScrolled] = useState(false);

  const handleScroll = (e) => {
    const bottom =
      e.target.scrollHeight - e.target.scrollTop === e.target.clientHeight;
    if (!bottom) {
      setHasUserScrolled(true);
    } else {
      setHasUserScrolled(false);
    }
  };

  useEffect(() => {
    setHasUserScrolled(false);
  }, [appId, deployId]);

  useEffect(() => {
    if (logPaneRef.current === null || hasUserScrolled) {
      return;
    }
    logPaneRef.current.children[0]?.lastElementChild?.scrollIntoView({
      // behavior: "smooth",
    });
  }, [log, hasUserScrolled]);

  useEffect(() => {
    setLog([]);
    if (!deployId || !appId) {
      return;
    }

    const controller = new AbortController();
    (async () => {
      try {
        await subscribeToLogStream(
          deployId,
          appId,
          (message: EventSourceMessage) => {
            const { event, data } = message;
            if (event === DeployLogEventType.LogLine) {
              setLog((log) => {
                return [...log, data];
              });
            } else if (event === DeployLogEventType.Done) {
              console.log("log stream done");
              controller.abort();
              setDone(true);
            }
          },
          controller,
        );
      } catch (e) {
        if (e instanceof AbortError) {
          console.log("log stream aborted");
        } else {
          throw e;
        }
      }
    })();
    return () => {
      console.log("aborting log stream");
      controller.abort();
    };
  }, [deployId, appId, subscribeToLogStream]);

  return (
    <Card className="size-full bg-gray-800 p-2 text-white">
      <div
        ref={logPaneRef}
        onScroll={handleScroll}
        className={"flex size-full flex-col overflow-auto p-2 text-xs"}
      >
        <Ansi linkify useClasses className={"whitespace-pre-wrap"}>
          {log.join("")}
        </Ansi>
        <span className="mt-4 font-mono font-bold text-green-300">
          {done ? (
            "Done"
          ) : (
            <AiOutlineLoading3Quarters
              size={11}
              className={"animate-spin text-gray-400"}
            />
          )}
        </span>
      </div>
    </Card>
  );
};
