import type { AppTemplate } from "../shared/models/AppTemplate.ts";
import { createContext } from "react";

type AppChooserContextProps = {
  apps: AppTemplate[];
  setApps: (apps: AppTemplate[]) => void;
  selectedApps: string[];
  setSelectedApps: (apps: string[]) => void;
};
export const AppChooserContext = createContext<AppChooserContextProps>({
  apps: [],
  setApps: () => {},
  selectedApps: [],
  setSelectedApps: () => {},
});
