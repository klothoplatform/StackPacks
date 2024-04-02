import { useContext } from "react";
import { StepperContext } from "../context/StepperContext.ts";

export const useStepper = () => {
  const context = useContext(StepperContext);
  if (!context) {
    throw new Error("useActiveTab must be used within an ActiveTabProvider");
  }
  return context;
};
