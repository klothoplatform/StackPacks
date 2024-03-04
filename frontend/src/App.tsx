import React, { type FC, useEffect } from "react";
import useApplicationStore from "./pages/store/ApplicationStore";
import { useAuth0 } from "@auth0/auth0-react";
import {
  createBrowserRouter,
  Navigate,
  Outlet,
  RouterProvider,
} from "react-router-dom";
import { CallbackPage } from "./pages/CallbackPage";
import OnboardingPage from "./pages/onboarding/OnboardingPage.tsx";
import { Auth0ProviderWithNavigate } from "./auth/Auth0ProviderWithNavigate.tsx";
import FallbackPage from "./pages/FallbackPage.tsx";
import UserDashboardPage from "./pages/user-dashboard/UserDashboardPage.tsx";
import { YourStackPane } from "./pages/user-dashboard/YourStackPane.tsx";
import { DeploymentLogsPane } from "./pages/user-dashboard/DeploymentLogsPane.tsx";
import { DeploymentLogViewerPane } from "./pages/user-dashboard/DeploymentLogViewerPane.tsx";

const AuthorizedOutlet: FC = () => {
  const { updateAuthentication } = useApplicationStore();
  const authContext = useAuth0();

  useEffect(() => {
    (async () => await updateAuthentication(authContext))();
  }, [authContext, updateAuthentication]);

  return <Outlet />;
};

const App: FC = function () {
  return (
    <Auth0ProviderWithNavigate>
      <AuthorizedOutlet />
    </Auth0ProviderWithNavigate>
  );
};

const AppRouter: FC = function () {
  const router = createBrowserRouter([
    {
      errorElement: <FallbackPage />,
      path: "",
      element: <App />,
      children: [
        { element: <Navigate to={"/onboarding"} />, index: true },
        { path: "callback", element: <CallbackPage /> },
        { path: "onboarding", element: <OnboardingPage /> },
        { path: "onboarding/:step", element: <OnboardingPage /> },
        {
          path: "user/dashboard",
          element: <UserDashboardPage />,
          children: [
            { element: <YourStackPane />, index: true },
            {
              path: "deployment-logs",
              children: [
                {
                  element: <DeploymentLogsPane />,
                  index: true,
                },
                {
                  path: ":runId",
                  element: <DeploymentLogViewerPane />,
                },
              ],
            },
          ],
        },
      ],
    },
  ]);

  return <RouterProvider router={router} />;
};

export default AppRouter;
