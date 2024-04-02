import type { Stackpack } from "../shared/models/Stackpack.ts";
import { createContext } from "react";

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
