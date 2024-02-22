import React, { useEffect, useState } from "react";
import { withAuthenticationRequired } from "@auth0/auth0-react";
import useApplicationStore from "./store/ApplicationStore";
import { WorkingOverlay } from "../components/WorkingOverlay";
import { ErrorOverlay } from "../components/ErrorOverlay";
import { SidebarProvider } from "../context/SidebarContext";
import { FallbackRenderer } from "../components/FallbackRenderer";
import { trackError } from "./store/ErrorStore";
import { UIError } from "../shared/errors";
import { ErrorBoundary } from "react-error-boundary";
import {
  HeaderNavBar,
  HeaderNavBarRow1Right,
} from "../components/HeaderNavBar";
import { Sidebar } from "flowbite-react";

function StacksPage() {
  const { isAuthenticated, user, addError } = useApplicationStore();
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || isLoaded) {
      return;
    }
    setIsLoaded(true);
  }, [isAuthenticated, isLoaded, addError]);

  return (
    <div
      className={
        "min-w-screen max-w-screen absolute flex h-screen max-h-screen min-h-screen w-screen flex-col overflow-hidden dark:bg-gray-800"
      }
    >
      <ErrorBoundary
        fallbackRender={FallbackRenderer}
        onError={(error, info) => {
          trackError(
            new UIError({
              message: "uncaught error in ArchitectureListPage",
              errorId: "ArchitectureListPage:ErrorBoundary",
              cause: error,
              data: {
                info,
              },
            }),
          );
        }}
      >
        <SidebarProvider>
          <HeaderNavBar>
            <div className="flex justify-end pb-2 pt-1">
              <HeaderNavBarRow1Right
                user={user}
                isAuthenticated={isAuthenticated}
              />
            </div>
          </HeaderNavBar>
          <div className="flex size-full flex-row overflow-hidden">
            <Sidebar />
            <div className="flex size-full grow flex-col gap-6 px-4 py-6">
              <div
                className={
                  "flex min-h-fit w-full flex-col gap-2 rounded-lg bg-gray-100 p-4 dark:bg-gray-900"
                }
              >
                <h2 className={"mb-2 text-lg font-semibold dark:text-white"}>
                  Create a new stack
                </h2>
              </div>
              <div
                className={
                  "bg-white-100 flex w-full grow flex-col gap-2 overflow-hidden rounded-lg p-4 dark:bg-gray-800"
                }
              >
                <h2 className={"mb-2 text-lg font-semibold dark:text-white"}>
                  Stacks
                </h2>
                <div className="size-full overflow-auto p-4"></div>
              </div>
            </div>
          </div>
        </SidebarProvider>
        <ErrorOverlay />
        <WorkingOverlay show={false} message={"Loading architectures..."} />
      </ErrorBoundary>
    </div>
  );
}

export default withAuthenticationRequired(StacksPage, {
  onRedirecting: () => (
    <WorkingOverlay show={true} message="Authenticating..." />
  ),
});
