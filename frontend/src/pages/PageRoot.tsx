import React, { useEffect, useState } from "react";
import { withAuthenticationRequired } from "@auth0/auth0-react";
import useApplicationStore from "./store/ApplicationStore.ts";
import { WorkingOverlay } from "../components/WorkingOverlay.tsx";
import { ErrorOverlay } from "../components/ErrorOverlay.tsx";
import { FallbackRenderer } from "../components/FallbackRenderer.tsx";
import { trackError } from "./store/ErrorStore.ts";
import { UIError } from "../shared/errors.ts";
import { ErrorBoundary } from "react-error-boundary";
import {
  HeaderNavBar,
  HeaderNavBarRow1Right,
} from "../components/HeaderNavBar.tsx";

export interface PageRootProps {
  onLoading?: () => void | Promise<void>;
  children: React.ReactNode;
}

export const PageRoot = withAuthenticationRequired(
  ({ onLoading, children }: PageRootProps) => {
    const { isAuthenticated, user } = useApplicationStore();
    const [isLoaded, setIsLoaded] = useState(false);

    useEffect(() => {
      if (!isAuthenticated || isLoaded) {
        return;
      }

      (async () => {
        await onLoading?.();
        setIsLoaded(true);
      })();
    }, [isAuthenticated, isLoaded, onLoading]);

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
                message: "uncaught error in PageRoot",
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
          {children}
          <ErrorOverlay />
        </ErrorBoundary>
      </div>
    );
  },
  {
    onRedirecting: () => (
      <WorkingOverlay show inset message="Authenticating..." />
    ),
  },
);
