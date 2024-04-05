import type { Step } from "../../context/StepperContext.ts";
import { ChooseAppStep } from "./ChooseAppStep.tsx";
import { ConfigureAppStep } from "./ConfigureAppStep.tsx";
import { UpdateRoleStep } from "./UpdateRoleStep.tsx";
import { DeployAppStep } from "./DeployAppStep.tsx";
import useApplicationStore from "../store/ApplicationStore.ts";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { FC } from "react";
import React, { useEffect } from "react";
import { ErrorBoundary } from "react-error-boundary";
import { FallbackRenderer } from "../../components/FallbackRenderer.tsx";
import { trackError } from "../store/ErrorStore.ts";
import { UIError } from "../../shared/errors.ts";
import { ErrorOverlay } from "../../components/ErrorOverlay.tsx";
import { StepperProvider } from "../../context/StepperProvider.tsx";
import { useStepper } from "../../hooks/useStepper.ts";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import { Stepper } from "../../components/Stepper.tsx";
import { FaRegCircle } from "react-icons/fa6";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";

type WorkflowStep = Step & {
  component: React.FC<any>;
  props?: Record<string, any>;
};

export function AddAppPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const selectedApp = searchParams.get("selectedApps");

  const workflowSteps: Array<WorkflowStep> = [
    {
      id: "choose-app",
      title: "Choose App",
      component: ChooseAppStep,
    },
    {
      id: "configure",
      title: "Configure",
      component: ConfigureAppStep,
      props: {
        selectedApp: selectedApp,
      },
    },
    {
      id: "update-deployment-role",
      title: "Update Deployment Role",
      component: UpdateRoleStep,
    },
    {
      id: "deploy",
      title: "Deploy",
      component: DeployAppStep,
      props: {
        selectedApp: selectedApp,
      },
    },
  ];

  const { project } = useApplicationStore();
  useEffectOnMount(() => {
    if (!project?.region) {
      navigate("/onboarding");
    }
  });

  return (
    <div className={"flex size-full flex-col overflow-hidden"}>
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
        <div className="flex size-full flex-row justify-center overflow-hidden">
          <div className="flex size-full max-w-[1400px] grow flex-col gap-6">
            <StepperProvider
              steps={workflowSteps}
              onGoBack={(step) =>
                navigate({
                  pathname: `./${step.id}`,
                  search: searchParams.toString(),
                })
              }
              onGoForwards={(step) =>
                navigate({
                  pathname: `./${step.id}`,
                  search: searchParams.toString(),
                })
              }
            >
              <AddAppsWorkflow />
            </StepperProvider>
          </div>
        </div>
        <ErrorOverlay />
      </ErrorBoundary>
    </div>
  );
}

const AddAppsWorkflow: FC = () => {
  const mainStepperContext = useStepper();
  const { currentStep, setCurrentStep, steps } = mainStepperContext;
  const { step: stepParam } = useParams();
  const navigate = useNavigate();
  const { resetOnboardingWorkflowState } = useApplicationStore();

  useDocumentTitle("StackSnap - Add Application");

  useEffect(() => {
    const resolvedStep = steps.findIndex((s) => s.id === stepParam);
    if (resolvedStep > -1) {
      setCurrentStep(resolvedStep);
      if (resolvedStep < currentStep) {
        // if the user navigated back using history, navigate forward to the same step to ensure
        // the only path forward is by progressing in the app
        navigate(`./${steps[resolvedStep].id}`);
      }
    } else if (steps.length) {
      navigate(`./${steps[0].id}`);
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

  const CurrentStepComponent = (steps[currentStep] as WorkflowStep)?.component;

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

      <CurrentStepComponent
        {...mainStepperContext}
        {...(steps[currentStep] as WorkflowStep).props}
      />
    </>
  );
};
