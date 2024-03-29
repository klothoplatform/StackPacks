import React, {
  type ComponentProps,
  type FC,
  useEffect,
  useState,
} from "react";
import { withAuthenticationRequired } from "@auth0/auth0-react";
import useApplicationStore from "../../store/ApplicationStore.ts";
import { WorkingOverlay } from "../../../components/WorkingOverlay.tsx";
import { ErrorOverlay } from "../../../components/ErrorOverlay.tsx";
import { FallbackRenderer } from "../../../components/FallbackRenderer.tsx";
import { trackError } from "../../store/ErrorStore.ts";
import { UIError } from "../../../shared/errors.ts";
import { ErrorBoundary } from "react-error-boundary";
import {
  HeaderNavBar,
  HeaderNavBarRow1Right,
} from "../../../components/HeaderNavBar.tsx";
import { Button, Sidebar, useThemeMode } from "flowbite-react";
import { Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import { WorkflowType } from "../../../shared/models/Workflow.ts";
import { GoHome } from "react-icons/go";
import classNames from "classnames";
import { statusIcons } from "../../../shared/StatusIcons.tsx";
import { titleCase } from "title-case";
import { FaArrowLeft } from "react-icons/fa6";
import { useInterval } from "usehooks-ts";

interface SidebarGroup {
  title?: string;
  items: {
    id: string;
    path: string;
    label: string;
    icon?: FC<ComponentProps<"svg">>;
  }[];
}

function WorkflowRunPage() {
  const {
    isAuthenticated,
    user,
    getProject,
    getStackPacks,
    getWorkflowRun,
    workflowRun,
  } = useApplicationStore();
  const [isLoaded, setIsLoaded] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { mode } = useThemeMode();

  const { runNumber, workflowType, appId } = useParams();
  const [interval, setInterval] = useState<number | null>(null);

  useInterval(async () => {
    const run = await getWorkflowRun({
      workflowType: workflowType.toUpperCase() as WorkflowType,
      appId,
      runNumber: parseInt(runNumber, 10),
    });
    if (run.completed_at) {
      setInterval(null);
    }
  }, interval);

  const sidebarConfig: SidebarGroup[] = [
    {
      title: undefined,
      items: [
        {
          id: "summary",
          path: `/project${appId ? "/apps/" + appId : ""}/workflows/${workflowType}/runs/${runNumber}`,
          label: "Summary",
          icon: GoHome,
        },
      ],
    },
    {
      title: "Jobs",
      items:
        workflowRun?.jobs?.map((job) => ({
          id: `job-${job.id}`,
          path: `jobs/${job.job_number}`,
          label: job.title,
          icon: () => statusIcons[job.status]?.medium,
        })) ?? [],
    },
  ];

  const activeItem = sidebarConfig
    .flatMap((group) => group.items ?? [])
    .find((item) => location.pathname.endsWith(item.path))?.id;

  useEffect(() => {
    if (!isAuthenticated || isLoaded) {
      return;
    }
    console.log({ appId, runNumber, workflowType });
    (async () => {
      try {
        await Promise.all([getProject(true), getStackPacks(true)]);
        const run = await getWorkflowRun({
          workflowType: workflowType.toUpperCase() as WorkflowType,
          appId,
          runNumber: parseInt(runNumber, 10),
        });
        if (!run.completed_at) {
          setInterval(10000);
        }
        setIsLoaded(true);
      } catch (error) {
        trackError(
          new UIError({
            message: "error loading project",
            errorId: "WorkflowsPage:useEffect:getUserStack",
            cause: error,
          }),
        );
      }
    })();
  }, [
    getStackPacks,
    getProject,
    isAuthenticated,
    isLoaded,
    getWorkflowRun,
    workflowType,
    runNumber,
    appId,
  ]);

  return (
    <div
      className={
        "min-w-screen max-w-screen absolute flex h-screen min-h-screen w-screen flex-col overflow-hidden bg-gradient-light dark:bg-gradient-dark dark:text-white"
      }
    >
      <ErrorBoundary
        fallbackRender={FallbackRenderer}
        onError={(error, info) => {
          trackError(
            new UIError({
              message: "uncaught error in WorkflowsPage",
              errorId: "WorkflowsPage:ErrorBoundary",
              cause: error,
              data: {
                info,
              },
            }),
          );
        }}
      >
        <HeaderNavBar>
          <div className="flex justify-end pb-2 pt-1">
            <HeaderNavBarRow1Right
              user={user}
              isAuthenticated={isAuthenticated}
            />
          </div>
        </HeaderNavBar>
        <div className={"flex size-full overflow-hidden"}>
          <Sidebar className={"z-5 min-w-fit"}>
            <Button
              color={mode}
              className={"w-fit"}
              size={"xs"}
              onClick={() =>
                navigate("../..", {
                  relative: "path",
                })
              }
            >
              <span className={"flex items-center gap-2 whitespace-nowrap"}>
                <FaArrowLeft />
                {workflowType === WorkflowType.Any
                  ? "All Workflows"
                  : titleCase(workflowType.toLowerCase())}
              </span>
            </Button>
            {!!workflowRun && (
              <div className="mt-2 flex items-center gap-2 text-2xl font-medium">
                {statusIcons[workflowRun?.status].large}
                {titleCase(workflowRun?.workflow_type.toLowerCase() ?? "")}
                <span className="font-normal text-gray-700 dark:text-gray-400">
                  {`#${runNumber}`}
                </span>
              </div>
            )}
            <Sidebar.Items>
              {sidebarConfig.map((group, index) => (
                <Sidebar.ItemGroup title={group.title} key={index}>
                  <span
                    className={classNames(
                      "text-xs font-bold text-gray-700 dark:text-gray-400",
                      {
                        "px-5": !group.items.some((item) => item.icon),
                        "px-3": group.items.some((item) => item.icon),
                      },
                    )}
                  >
                    {group.title}
                  </span>
                  {group.items.map((item) => (
                    <Sidebar.Item
                      className={classNames("text-sm h-fit py-1", {
                        "font-normal": !!group.title,
                      })}
                      icon={item.icon}
                      key={item.id}
                      id={item.id}
                      active={activeItem === item.id}
                      onClick={() => navigate(item.path)}
                    >
                      {item.label}
                    </Sidebar.Item>
                  ))}
                </Sidebar.ItemGroup>
              ))}
            </Sidebar.Items>
          </Sidebar>
          {isLoaded ? (
            <div className="flex size-full grow flex-col gap-6 overflow-hidden p-6">
              <Outlet />
            </div>
          ) : (
            <WorkingOverlay show={true} message="Loading..." />
          )}
        </div>
        <ErrorOverlay />
      </ErrorBoundary>
    </div>
  );
}

const AuthenticatedWorkflowsPage = withAuthenticationRequired(WorkflowRunPage, {
  onRedirecting: () => (
    <WorkingOverlay show={true} message="Authenticating..." />
  ),
});

export default AuthenticatedWorkflowsPage;
