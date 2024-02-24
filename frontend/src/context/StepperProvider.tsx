import type { FC, PropsWithChildren } from "react";
import React from "react";
import type { Step } from "./StepperContext";
import { StepperContext } from "./StepperContext";

export const StepperProvider: FC<PropsWithChildren> = ({ children }) => {
  const [currentStep, setCurrentStep] = React.useState(0);
  const [steps, setSteps] = React.useState<Step[]>([]);
  const goForwards = () =>
    setCurrentStep((prev) =>
      prev + 1 >= steps.length ? steps.length - 1 : prev + 1,
    );
  const goBack = () => setCurrentStep((prev) => (prev - 1 < 0 ? 0 : prev - 1));
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
