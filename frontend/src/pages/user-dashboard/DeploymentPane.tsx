import type { FC } from "react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";

export const DeploymentPane: FC = () => {
  useDocumentTitle("StackSnap - Deployment Logs");

  return <div>Deployment Logs</div>;
};
