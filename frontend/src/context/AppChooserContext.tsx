import type { Stackpack } from "../shared/models/Stackpack.ts";
import { createContext, useContext } from "react";

type AppChooserContextProps = {
  apps: Stackpack[];
  setApps: (apps: Stackpack[]) => void;
  selectedApps: string[];
  setSelectedApps: (apps: string[]) => void;
};
export const AppChooserContext = createContext<AppChooserContextProps>({
  apps: [],
  setApps: () => {},
  selectedApps: [],
  setSelectedApps: () => {},
});

export const useAppChooser = () => {
  const context = useContext(AppChooserContext);
  if (!context) {
    throw new Error("useAppChooser must be used within an AppChooserProvider");
  }
  return context;
};
