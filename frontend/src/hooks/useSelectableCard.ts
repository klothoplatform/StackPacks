import { useContext } from "react";
import { StepperContext } from "../context/StepperContext.tsx";

export const useSelectableCard = () => {
  const context = useContext(StepperContext);
  if (!context) {
    throw new Error("useSelectableCard must be used within a SelectableCard");
  }
  return context;
};
