import React, { useEffect, useState } from "react";
import { withAuthenticationRequired } from "@auth0/auth0-react";
import useApplicationStore from "../store/ApplicationStore";
import { WorkingOverlay } from "../../components/WorkingOverlay";
import { ErrorOverlay } from "../../components/ErrorOverlay";
import { FallbackRenderer } from "../../components/FallbackRenderer";
import { trackError } from "../store/ErrorStore";
import { UIError } from "../../shared/errors";
import { ErrorBoundary } from "react-error-boundary";
import {
  HeaderNavBar,
  HeaderNavBarRow1Right,
} from "../../components/HeaderNavBar";
import { Stepper } from "../../components/Stepper";
import { FaRegCircle } from "react-icons/fa6";
import type { Step } from "../../context/StepperContext";
import { useStepper } from "../../hooks/useStepper";
import { StepperProvider } from "../../context/StepperProvider";
import { ChooseAppsStep } from "./ChooseAppsStep";
import { ConnectAccountStep } from "./ConnectAccountStep";
import { DeploymentStep } from "./DeploymentStep";
import { ConfigureAppsStep } from "./ConfigureAppsStep.tsx";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";

const workflowSteps: Array<Step & { component: React.FC<any> }> = [
  {
    id: "choose-apps",
    title: "Choose Apps",
    component: ChooseAppsStep,
  },
  {
    id: "connect-account",
    title: "Connect Account",
    component: ConnectAccountStep,
  },
  {
    id: "configure-stack",
    title: "Configure Stack",
    component: ConfigureAppsStep,
  },
  {
    id: "deploy",
    title: "Deploy",
    component: DeploymentStep,
  },
];

function OnboardingPage() {
  const { isAuthenticated, user, addError } = useApplicationStore();
  const [isLoaded, setIsLoaded] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    loadUserStack,
    updateOnboardingWorkflowState,
    onboardingWorkflowState: { selectedStackPacks },
  } = useApplicationStore();
  const navigate = useNavigate();
  const [canOnboard, setCanOnboard] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || isLoaded) {
      return;
    }
    (async () => {
      try {
        const userStack = await loadUserStack();
        if (!userStack) {
          setCanOnboard(true);
        } else {
          navigate("/user/dashboard", { replace: true });
        }
      } catch (e: any) {
        addError(
          new UIError({
            message: "An error occurred. Please try again later",
            cause: e,
          }),
        );
      } finally {
        setIsLoaded(true);
      }
    })();
  }, [isAuthenticated, isLoaded, loadUserStack, navigate, addError]);

  useEffectOnMount(() => {
    if (selectedStackPacks.length > 0) {
      setSearchParams({ selectedApps: selectedStackPacks.join(",") });
    } else {
      const queryApps = searchParams
        .get("selectedApps")
        ?.split(",")
        ?.filter((qa) => qa);
      if (queryApps?.length > 0) {
        updateOnboardingWorkflowState({
          selectedStackPacks: queryApps,
        });
      }
    }
  });

  return (
    <div
      className={
        "min-w-screen max-w-screen absolute flex h-screen min-h-screen w-screen flex-col overflow-hidden bg-white dark:bg-gray-900"
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
        <HeaderNavBar>
          <div className="flex justify-end pb-2 pt-1">
            <HeaderNavBarRow1Right
              user={user}
              isAuthenticated={isAuthenticated}
            />
          </div>
        </HeaderNavBar>
        {canOnboard && (
          <div className="flex size-full flex-row justify-center overflow-hidden">
            <div className="flex size-full max-w-[1000px] grow flex-col gap-6 p-6">
              <StepperProvider
                onGoBack={(step) =>
                  navigate(
                    {
                      pathname: `../${step.id}`,
                      search: searchParams.toString(),
                    },
                    { relative: "path" },
                  )
                }
                onGoForwards={(step) =>
                  navigate(
                    {
                      pathname: `../${step.id}`,
                      search: searchParams.toString(),
                    },
                    { relative: "path" },
                  )
                }
              >
                <OnboardingWorkflow />
              </StepperProvider>
            </div>
          </div>
        )}

        <ErrorOverlay />
        <WorkingOverlay show={false} message={"Loading architectures..."} />
      </ErrorBoundary>
    </div>
  );
}

const OnboardingWorkflow: React.FC = () => {
  const mainStepperContext = useStepper();
  const { currentStep, setCurrentStep, setSteps, steps } = mainStepperContext;
  const { step: stepParam } = useParams();
  const navigate = useNavigate();
  const { resetOnboardingWorkflowState } = useApplicationStore();

  const stepTitle = steps.find((s) => s.id === stepParam)?.title;
  useDocumentTitle(
    "StackPacks - Onboarding" + (stepTitle ? ` - ${stepTitle}` : ""),
  );

  useEffect(() => {
    setSteps(workflowSteps);
  }, [setSteps]);

  useEffect(() => {
    const resolvedStep = steps.findIndex((s) => s.id === stepParam);
    if (resolvedStep > -1) {
      setCurrentStep(resolvedStep);
      if (resolvedStep < currentStep) {
        // if the user navigated back using history, navigate forward to the same step to ensure
        // the only path forward is by progressing in the app
        navigate(`/onboarding/${steps[resolvedStep].id}`);
      }
    } else if (steps.length) {
      navigate(`/onboarding/${steps[0].id}`);
      // navigating to /onboarding without a step indicates a fresh session
      resetOnboardingWorkflowState();
    }
  }, [
    stepParam,
    steps,
    setCurrentStep,
    currentStep,
    navigate,
    resetOnboardingWorkflowState,
  ]);

  const CurrentStepComponent = workflowSteps[currentStep]?.component;

  return (
    <>
      <div className="flex w-full justify-center">
        <Stepper
          steps={steps}
          uncompletedStepIcon={<FaRegCircle />}
          currentStepColor={"purple"}
          completedStepColor={"purple"}
          activeStep={currentStep}
        />
      </div>
      <CurrentStepComponent {...mainStepperContext} />
    </>
  );
};

const AuthenticatedOnboardingPage = withAuthenticationRequired(OnboardingPage, {
  onRedirecting: () => (
    <WorkingOverlay show={true} message="Authenticating..." />
  ),
});

export default AuthenticatedOnboardingPage;
