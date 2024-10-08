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
import { Auth0ProviderWithNavigate } from "./auth/Auth0ProviderWithNavigate.tsx";
import FallbackPage from "./pages/FallbackPage.tsx";
import UserDashboardPage from "./pages/ProjectPage/ProjectRootPage.tsx";
import { ProjectPage } from "./pages/ProjectPage/ProjectPage.tsx";
import { ConfigureAppPage } from "./pages/ConfigureApp/ConfigureAppPage.tsx";
import { AddAppPage } from "./pages/AddAppPage/AddAppPage.tsx";
import WorkflowsPage from "./pages/Workflows/WorkflowsRootPage.tsx";
import { WorkflowRunsPage } from "./pages/Workflows/WorkflowRunsPage.tsx";
import { RunOverviewPage } from "./pages/Workflows/WorkflowRunPage/RunOverviewPage.tsx";
import { JobDetailsPage } from "./pages/Workflows/WorkflowRunPage/JobDetailsPage.tsx";
import WorkflowRunPage from "./pages/Workflows/WorkflowRunPage/WorkflowRunPage.tsx";
import { ConfigureEnvironmentPage } from "./pages/ConfigureEnvironmentPage.tsx";
import { OnboardingPage } from "./pages/OnboardingPage/OnboardingPage.tsx";

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
        { element: <Navigate to={"/project"} />, index: true },
        { path: "callback", element: <CallbackPage /> },
        {
          path: "/onboarding",
          element: <OnboardingPage />,
          children: [
            {
              path: ":step",
              element: <AddAppPage />,
              index: true,
            },
          ],
        },
        {
          path: "/project",
          element: <UserDashboardPage />,
          children: [
            { element: <ProjectPage />, index: true },
            {
              path: "add-apps",
              element: <AddAppPage />,
              children: [
                {
                  path: ":step",
                  element: <AddAppPage />,
                  index: true,
                },
              ],
            },
            {
              path: "environment",
              element: <ConfigureEnvironmentPage />,
            },
            {
              path: "apps/:appId",
              children: [
                {
                  path: "configure",
                  element: <ConfigureAppPage />,
                },
              ],
            },
          ],
        },
        {
          path: "/project/apps/:appId/workflows",
          element: <WorkflowsPage />,
          children: [
            {
              index: true,
              element: <WorkflowRunsPage />,
            },
            {
              path: ":workflowType",
              element: <WorkflowRunsPage />,
            },
          ],
        },
        {
          path: "/project/workflows/:workflowType/runs/:runNumber",
          element: <WorkflowRunPage />,
          children: [
            {
              index: true,
              element: <RunOverviewPage />,
            },
            {
              path: "jobs/:jobNumber",
              element: <JobDetailsPage />,
            },
          ],
        },
        {
          path: "/project/workflows",
          element: <WorkflowsPage />,
          children: [
            {
              index: true,
              element: <WorkflowRunsPage />,
            },
            {
              path: ":workflowType",
              element: <WorkflowRunsPage />,
            },
          ],
        },
        {
          path: "/project/apps/:appId/workflows/:workflowType/runs/:runNumber",
          element: <WorkflowRunPage />,
          children: [
            {
              index: true,
              element: <RunOverviewPage />,
            },
            {
              path: "jobs/:jobNumber",
              element: <JobDetailsPage />,
            },
          ],
        },
      ],
    },
  ]);

  return <RouterProvider router={router} />;
};
export default AppRouter;
