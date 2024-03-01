import type { FC, PropsWithChildren } from "react";
import React from "react";
import type { Step } from "./StepperContext";
import { StepperContext } from "./StepperContext";

export const StepperProvider: FC<
  PropsWithChildren<{
    onGoBack?: (step: Step) => void;
    onGoForwards?: (step: Step) => void;
    activeStep?: number;
  }>
> = ({ children, onGoBack, onGoForwards, activeStep }) => {
  const [currentStep, setCurrentStep] = React.useState(activeStep || 0);
  const [steps, setSteps] = React.useState<Step[]>([]);
  const goForwards = () => {
    const nextStep =
      currentStep + 1 >= steps.length ? steps.length - 1 : currentStep + 1;
    setCurrentStep(nextStep);
    onGoForwards?.(steps[nextStep]);
  };

  const goBack = () => {
    const previousStep = currentStep - 1 < 0 ? 0 : currentStep - 1;
    setCurrentStep(previousStep);
    onGoBack?.(steps[previousStep]);
  };
  const goToStep = (step: number | string) => {
    if (typeof step === "string") {
      step = steps.findIndex((s) => s.id === step);
    }
    if (step < 0 || step >= steps.length) {
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
    steps,
    setSteps,
  };

  return (
    <StepperContext.Provider value={value}>{children}</StepperContext.Provider>
  );
};
