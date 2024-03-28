import { LogViewer } from "./LogViewer.tsx";
import { useParams } from "react-router-dom";
import type { WorkflowType } from "../../../shared/models/Workflow.ts";

export const JobDetailsPage = () => {
  const { runNumber, jobNumber, workflowType, appId } = useParams();

  return (
    <div className="flex size-full flex-col gap-4">
      <h1 className="text-2xl font-medium">Job Details</h1>
      <LogViewer
        workflowType={workflowType.toUpperCase() as WorkflowType}
        appId={appId}
        runNumber={parseInt(runNumber)}
        jobNumber={parseInt(jobNumber)}
      />
    </div>
  );
};
