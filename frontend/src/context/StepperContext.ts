import type React from "react";
import { createContext } from "react";

export interface Step {
  id: number | string;
  title?: string;
  titleIcon?: React.ReactNode;
  subtitle?: string;
  informational?: boolean;
}

export interface StepperContextProps {
  currentStep: number;
  setCurrentStep: (step: number) => void;
  steps: Step[];
  setSteps: (steps: Step[]) => void;
  goForwards: () => void;
  goBack: () => void;
  goToStep: (step: number | string) => void;
}

export const StepperContext = createContext<StepperContextProps>({
  currentStep: 0,
  setCurrentStep: () => {},
  steps: [],
  setSteps: () => {},
  goForwards: () => {},
  goBack: () => {},
  goToStep: () => {},
});
