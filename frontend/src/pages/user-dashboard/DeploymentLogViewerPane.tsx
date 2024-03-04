import type { FC } from "react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import { useParams } from "react-router-dom";

export const DeploymentLogViewerPane: FC = () => {
  useDocumentTitle("StackPacks - Log Viewer");
  const { runId } = useParams();

  return <div>Log Viewer for run: {runId}</div>;
};
