import { useContext } from "react";
import { AppChooserContext } from "../context/AppChooserContext.tsx";

export const useAppChooser = () => {
  const context = useContext(AppChooserContext);
  if (!context) {
    throw new Error("useAppChooser must be used within an AppChooserProvider");
  }
  return context;
};
