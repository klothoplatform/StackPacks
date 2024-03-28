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
import { Sidebar, SidebarItem, SidebarItemGroup } from "flowbite-react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

const sidebarConfig = [
  {
    id: "your-stack",
    url: "/user/dashboard",
    title: "Your Stack",
  },
  {
    id: "workflows",
    url: "/project/workflows",
    title: "Workflows",
  },
];

function UserDashboardPage() {
  const { isAuthenticated, user, getProject, getStackPacks, project } =
    useApplicationStore();
  const [isLoaded, setIsLoaded] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const activeItem = sidebarConfig.find(
    (item) => item.url === location.pathname,
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
        trackError(
          new UIError({
            message: "error loading user stack",
            errorId: "UserDashboardPage:useEffect:getUserStack",
            cause: error,
          }),
        );
      }
    })();
  }, [getStackPacks, getProject, isAuthenticated, isLoaded]);

  useEffect(() => {
    if (isLoaded && !Object.keys(project?.stack_packs ?? {}).length) {
      navigate("./add-apps");
    }
  }, [isLoaded, navigate, project]);

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
              message: "uncaught error in UserDashboardPage",
              errorId: "UserDashboardPage:ErrorBoundary",
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
            <SidebarItemGroup>
              {sidebarConfig.map((item) => (
                <SidebarItem
                  key={item.id}
                  active={item.id === activeItem}
                  onClick={() => navigate(item.url)}
                >
                  {item.title}
                </SidebarItem>
              ))}
            </SidebarItemGroup>
          </Sidebar>
          <div className="flex size-full grow flex-col gap-6 overflow-hidden p-6">
            {isLoaded && <Outlet />}
          </div>
        </div>
        <ErrorOverlay />
        <WorkingOverlay show={false} message={"Loading architectures..."} />
      </ErrorBoundary>
    </div>
  );
}

const AuthenticatedUserDashboardPage = withAuthenticationRequired(
  UserDashboardPage,
  {
    onRedirecting: () => (
      <WorkingOverlay show={true} message="Authenticating..." />
    ),
  },
);

export default AuthenticatedUserDashboardPage;
