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
import { HiSquare3Stack3D } from "react-icons/hi2";
import { useScreenSize } from "../../hooks/useScreenSize.ts";
import { FaPlus } from "react-icons/fa6";
import { PiTreeStructureFill } from "react-icons/pi";

const sidebarConfig = [
  {
    icon: HiSquare3Stack3D,
    id: "your-project",
    url: "/project",
    title: "Your Project",
    exact: true,
  },
  {
    icon: FaPlus,
    id: "add-apps",
    url: "/project/add-apps",
    title: "Add New App",
  },
  {
    icon: PiTreeStructureFill,
    id: "workflows",
    url: "/project/workflows",
    title: "Workflows",
  },
];

function ProjectRootPage() {
  const { isAuthenticated, user, getProject, getStackPacks, project } =
    useApplicationStore();
  const [isLoaded, setIsLoaded] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const activeItem = sidebarConfig.find((item) =>
    item.exact
      ? location.pathname === item.url
      : location.pathname.startsWith(item.url),
  )?.id;
  const { isXSmallScreen } = useScreenSize();

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
            message: "error loading your project",
            errorId: "ProjectRootPage:useEffect:getProject",
            cause: error,
          }),
        );
      }
    })();
  }, [getStackPacks, getProject, isAuthenticated, isLoaded]);

  useEffect(() => {
    if (isLoaded && isAuthenticated && !project?.id) {
      navigate("/onboarding");
    }
  }, [isAuthenticated, isLoaded, navigate, project]);

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
              message: "uncaught error in ProjectRootPage",
              errorId: "ProjectRootPage:ErrorBoundary",
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
          <Sidebar className={"z-5"} collapsed={isXSmallScreen}>
            <SidebarItemGroup>
              {sidebarConfig.map((item) => (
                <SidebarItem
                  key={item.id}
                  active={item.id === activeItem}
                  onClick={() => navigate(item.url)}
                  icon={item.icon}
                >
                  {item.title}
                </SidebarItem>
              ))}
            </SidebarItemGroup>
          </Sidebar>
          {isLoaded ? (
            <div className="flex size-full grow flex-col gap-6 overflow-hidden p-6">
              <Outlet />
            </div>
          ) : (
            <WorkingOverlay show noOverlay message="Loading Project..." />
          )}
        </div>

        <ErrorOverlay />
      </ErrorBoundary>
    </div>
  );
}

const AuthenticatedUserDashboardPage = withAuthenticationRequired(
  ProjectRootPage,
  {
    onRedirecting: () => (
      <WorkingOverlay show={true} message="Authenticating..." />
    ),
  },
);

export default AuthenticatedUserDashboardPage;
