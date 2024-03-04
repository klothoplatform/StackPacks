import type { FC } from "react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";

export const DeploymentLogsPane: FC = () => {
  useDocumentTitle("StackPacks - Deployment Logs");

  return <div>Deployment Logs</div>;
};
