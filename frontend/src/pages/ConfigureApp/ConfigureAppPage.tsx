import type { FC } from "react";
import React, { useMemo } from "react";
import { UIError } from "../../shared/errors.ts";
import { ErrorBoundary } from "react-error-boundary";
import { useStepper } from "../../hooks/useStepper.ts";
import { StepperProvider } from "../../context/StepperProvider.tsx";
import type { Step } from "../../context/StepperContext.tsx";
import { FallbackRenderer } from "../../components/FallbackRenderer.tsx";
import { trackError } from "../store/ErrorStore.ts";
import { ConfigureAppStep } from "./ConfigureAppStep.tsx";
import { useNavigate, useParams } from "react-router-dom";
import { Button, useThemeMode } from "flowbite-react";
import { MdChevronLeft } from "react-icons/md";
import useApplicationStore from "../store/ApplicationStore.ts";
import { resolveStackpacks } from "../../shared/models/Stackpack.ts";

export const ConfigureAppPage: FC = () => {
  const { appId } = useParams();

  const { project, stackPacks } = useApplicationStore();

  const workflowSteps: Array<
    Step & { component: React.FC<any>; props?: Record<string, any> }
  > = useMemo(
    () => [
      {
        id: "configure-app",
        title: `Configure ${resolveStackpacks([appId], stackPacks)[0]?.name ?? appId}`,
        component: ConfigureAppStep,
        props: {
          appId,
        },
      },
    ],
    [appId, stackPacks],
  );

  const navigate = useNavigate();
  const mainStepperContext = useStepper();
  const { currentStep } = mainStepperContext;
  const { mode } = useThemeMode();

  const CurrentStepComponent = workflowSteps[currentStep]?.component;

  if (project?.stack_packs?.[appId] === undefined) {
    navigate("../../add-apps");
  }

  return (
    <StepperProvider>
      <ErrorBoundary
        fallbackRender={FallbackRenderer}
        onError={(error, info) => {
          trackError(
            new UIError({
              message: "Uncaught error in ConfigureAppWorkflow",
              errorId: "ConfigureAppWorkflow:ErrorBoundary",
              cause: error,
              data: {
                info,
              },
            }),
          );
        }}
      >
        <div className="flex max-w-xl flex-col justify-center gap-4 p-4">
          <div className="flex gap-4 px-1">
            <Button
              color={mode}
              outline
              size="xs"
              className="flex items-center gap-2 whitespace-nowrap"
              onClick={() => navigate("/project")}
            >
              <MdChevronLeft /> Back
            </Button>
            <h2 className="text-2xl font-medium">
              {workflowSteps[currentStep].title}
            </h2>
          </div>

          <CurrentStepComponent
            {...workflowSteps[currentStep].props}
            {...mainStepperContext}
          />
        </div>
      </ErrorBoundary>
    </StepperProvider>
  );
};
