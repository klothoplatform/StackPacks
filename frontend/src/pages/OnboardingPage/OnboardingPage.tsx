import type { Step } from "../../context/StepperContext.ts";
import useApplicationStore from "../store/ApplicationStore.ts";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { FC } from "react";
import React, { useEffect } from "react";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
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
import { PageRoot } from "../PageRoot.tsx";
import { ChooseAppsStep } from "./ChooseAppsStep.tsx";
import { ConfigureAppsStep } from "./ConfigureAppsStep.tsx";
import { ConnectAccountStep } from "./ConnectAccountStep.tsx";
import { DeploymentStep } from "./DeploymentStep.tsx";
import { AppLifecycleStatus } from "../../shared/models/Project.ts";

type WorkflowStep = Step & {
  component: React.FC<any>;
  props?: Record<string, any>;
};

export function OnboardingPage() {
  const [searchParams] = useSearchParams();
  const { updateOnboardingWorkflowState, project, getProject } =
    useApplicationStore();
  const navigate = useNavigate();

  const workflowSteps: Array<WorkflowStep> = [
    {
      id: "choose-apps",
      title: "Select Applications",
      component: ChooseAppsStep,
    },
    {
      id: "configure-software",
      title: "Configure",
      component: ConfigureAppsStep,
    },
    {
      id: "connect-account",
      title: "Connect Account",
      component: ConnectAccountStep,
    },
    {
      id: "deploy",
      title: "Deploy",
      component: DeploymentStep,
    },
  ];

  useEffectOnMount(() => {
    const queryApps = searchParams
      .get("selectedApps")
      ?.split(",")
      ?.filter((qa) => qa);
    if (queryApps?.length > 0) {
      updateOnboardingWorkflowState({
        selectedStackPacks: queryApps,
      });
    }
  });

  useEffect(() => {
    if (
      Object.values(project?.stack_packs ?? {}).some(
        (app) => app.status !== AppLifecycleStatus.New,
      )
    ) {
      navigate("/project");
    }
  }, [project, navigate]);

  return (
    <PageRoot
      onLoading={async () => {
        await getProject(true);
      }}
    >
      <div className={"flex size-full flex-col overflow-hidden"}>
        <ErrorBoundary
          fallbackRender={FallbackRenderer}
          onError={(error, info) => {
            trackError(
              new UIError({
                message: "uncaught error in OnboardingPage",
                errorId: "OnboardingPage:ErrorBoundary",
                cause: error,
                data: {
                  info,
                },
              }),
            );
          }}
        >
          <div className="flex size-full flex-row justify-center overflow-hidden">
            <div className="flex size-full max-w-[1400px] grow flex-col gap-6 p-6">
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
    </PageRoot>
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
