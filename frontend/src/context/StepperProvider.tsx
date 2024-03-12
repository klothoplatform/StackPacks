import type { FC, PropsWithChildren } from "react";
import { useEffect } from "react";
import React from "react";
import type { Step } from "./StepperContext";
import { StepperContext } from "./StepperContext";

export const StepperProvider: FC<
  PropsWithChildren<{
    onGoBack?: (step: Step) => void;
    onGoForwards?: (step: Step) => void;
    activeStep?: number;
    steps?: Step[];
  }>
> = ({ children, onGoBack, onGoForwards, activeStep, steps }) => {
  const [currentStep, setCurrentStep] = React.useState(activeStep || 0);
  const [_steps, setSteps] = React.useState<Step[]>(steps || []);

  useEffect(() => {
    setSteps(steps || []);
  }, [steps]);

  const goForwards = () => {
    const nextStep =
      currentStep + 1 >= _steps.length ? _steps.length - 1 : currentStep + 1;
    setCurrentStep(nextStep);
    onGoForwards?.(_steps[nextStep]);
  };

  const goBack = () => {
    const previousStep = currentStep - 1 < 0 ? 0 : currentStep - 1;
    setCurrentStep(previousStep);
    onGoBack?.(_steps[previousStep]);
  };
  const goToStep = (step: number | string) => {
    if (typeof step === "string") {
      step = _steps.findIndex((s) => s.id === step);
    }
    if (step < 0 || step >= _steps.length) {
      throw new Error("Invalid step");
    }
    setCurrentStep(step);
  };
  const value = {
    currentStep,
    setCurrentStep,
    goForwards,
    goBack,
    goToStep,
    steps: _steps,
    setSteps,
  };

  return (
    <StepperContext.Provider value={value}>{children}</StepperContext.Provider>
  );
};
