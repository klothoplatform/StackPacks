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
    id: "deployment-logs",
    url: "/user/dashboard/deployment-logs",
    title: "Deployment Logs",
  },
  {
    id: "latest-logs",
    url: "/user/dashboard/deployment-logs/latest",
    title: "Latest Logs",
  },
];

function UserDashboardPage() {
  const { isAuthenticated, user, addError } = useApplicationStore();
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
    setIsLoaded(true);
  }, [isAuthenticated, isLoaded]);

  return (
    <div
      className={
        "min-w-screen max-w-screen absolute flex h-screen min-h-screen w-screen flex-col overflow-hidden bg-white dark:bg-gray-900 dark:text-white"
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
        <div className={"flex size-full"}>
          <Sidebar>
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
          <div className="flex size-full flex-row justify-center overflow-hidden">
            <div className="flex size-full grow flex-col gap-6 p-6">
              <Outlet />
            </div>
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
