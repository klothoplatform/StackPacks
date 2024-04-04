import { LogViewer } from "./LogViewer.tsx";
import { useParams } from "react-router-dom";
import type { WorkflowType } from "../../../shared/models/Workflow.ts";
import { WorkflowJobStatus } from "../../../shared/models/Workflow.ts";
import useApplicationStore from "../../store/ApplicationStore.ts";
import { StatusReasonCard } from "../../../components/StatusReasonCard.tsx";

export const JobDetailsPage = () => {
  const { runNumber, jobNumber, workflowType, appId } = useParams();
  const { workflowRun } = useApplicationStore();

  const job = workflowRun?.jobs.find(
    (j) => j.job_number === parseInt(jobNumber, 10),
  );
  const statusReason = job?.status_reason;
  const jobStatus = job?.status;
  return (
    <div className="flex size-full flex-col gap-4">
      <LogViewer
        workflowType={workflowType.toUpperCase() as WorkflowType}
        appId={appId}
        job={job}
        runNumber={parseInt(runNumber, 10)}
      />
      {![
        WorkflowJobStatus.New,
        WorkflowJobStatus.InProgress,
        WorkflowJobStatus.Succeeded,
      ].includes(jobStatus) && <StatusReasonCard message={statusReason} />}
    </div>
  );
};
