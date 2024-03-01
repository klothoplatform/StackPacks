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
    title: "Configure",
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

  useEffect(() => {
    if (!isAuthenticated || isLoaded) {
      return;
    }
    setIsLoaded(true);
  }, [isAuthenticated, isLoaded, addError]);

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
        <div className="flex size-full flex-row justify-center overflow-hidden">
          <div className="flex size-full max-w-[1000px] grow flex-col gap-6 p-6">
            <StepperProvider>
              <OnboardingWorkflow />
            </StepperProvider>
          </div>
        </div>
        <ErrorOverlay />
        <WorkingOverlay show={false} message={"Loading architectures..."} />
      </ErrorBoundary>
    </div>
  );
}

const OnboardingWorkflow: React.FC = () => {
  const mainStepperContext = useStepper();
  const { currentStep, setCurrentStep, setSteps, steps, goBack, goForwards } =
    mainStepperContext;

  useEffect(() => {
    setSteps(workflowSteps);
  }, [setSteps]);

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
