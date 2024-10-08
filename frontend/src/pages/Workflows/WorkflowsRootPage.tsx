import React, { useEffect, useState } from "react";
import { withAuthenticationRequired } from "@auth0/auth0-react";
import useApplicationStore from "../store/ApplicationStore.ts";
import { WorkingOverlay } from "../../components/WorkingOverlay.tsx";
import { ErrorOverlay } from "../../components/ErrorOverlay.tsx";
import { FallbackRenderer } from "../../components/FallbackRenderer.tsx";
import { trackError } from "../store/ErrorStore.ts";
import { UIError } from "../../shared/errors.ts";
import { ErrorBoundary } from "react-error-boundary";
import {
  HeaderNavBar,
  HeaderNavBarRow1Right,
} from "../../components/HeaderNavBar.tsx";
import { Button, Sidebar, useThemeMode } from "flowbite-react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { WorkflowType } from "../../shared/models/Workflow.ts";
import { FaArrowLeft } from "react-icons/fa6";

interface SidebarGroup {
  title?: string;
  items: {
    id: string;
    path: string;
    label: string;
  }[];
}

const sidebarConfig: SidebarGroup[] = [
  {
    title: undefined,
    items: [
      {
        id: "all-workflows",
        path: "../workflows",
        label: "All Workflows",
      },
    ],
  },
  {
    title: "Workflows",
    items: Object.entries(WorkflowType)
      .filter(([_, key]) => key !== WorkflowType.Any)
      .map(([value, key]) => ({
        id: `workflow-${key.toLowerCase()}`,
        path: `./${key.toLowerCase()}`,
        label: value,
      })),
  },
];

function WorkflowsRootPage() {
  const { isAuthenticated, user, getProject, getStackPacks, addError } =
    useApplicationStore();
  const [isLoaded, setIsLoaded] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const activeItem = sidebarConfig
    .flatMap((group) => group.items)
    .find((item) =>
      location.pathname.endsWith(item.path.replace(/^(\.*\/)+/, "")),
    )?.id;

  useEffect(() => {
    if (!isAuthenticated || isLoaded) {
      return;
    }

    (async () => {
      try {
        await Promise.all([getProject(true), getStackPacks(true)]);
        setIsLoaded(true);
      } catch (error) {
        addError(
          new UIError({
            message: "error loading project",
            errorId: "WorkflowsRootPage:useEffect:getUserStack",
            cause: error,
          }),
        );
      }
    })();
  }, [getStackPacks, getProject, isAuthenticated, isLoaded, addError]);

  const { mode } = useThemeMode();

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
              message: "uncaught error in WorkflowsRootPage",
              errorId: "WorkflowsRootPage:ErrorBoundary",
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
          <Sidebar className={"z-5"}>
            <Button
              color={mode}
              className={"w-fit"}
              size={"xs"}
              onClick={() => navigate("/project")}
            >
              <span className={"flex items-center gap-2 whitespace-nowrap"}>
                <FaArrowLeft />
                <span>Project</span>
              </span>
            </Button>
            <Sidebar.Items>
              {sidebarConfig.map((group, index) => (
                <Sidebar.ItemGroup title={group.title} key={index}>
                  <span
                    className={
                      "px-5 text-xs font-bold text-gray-700 dark:text-gray-400"
                    }
                  >
                    {group.title}
                  </span>
                  {group.items.map((item) => (
                    <Sidebar.Item
                      key={item.id}
                      id={item.id}
                      active={activeItem === item.id}
                      onClick={() => navigate(item.path, { relative: "path" })}
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
            <WorkingOverlay show={true} message="Loading workflow runs..." />
          )}
        </div>
        <ErrorOverlay />
      </ErrorBoundary>
    </div>
  );
}

const AuthenticatedWorkflowsPage = withAuthenticationRequired(
  WorkflowsRootPage,
  {
    onRedirecting: () => (
      <WorkingOverlay noOverlay show message="Authenticating..." />
    ),
  },
);

export default AuthenticatedWorkflowsPage;
