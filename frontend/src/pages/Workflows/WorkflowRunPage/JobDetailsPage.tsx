import { LogViewer } from "./LogViewer.tsx";
import { useParams } from "react-router-dom";
import type { WorkflowType } from "../../../shared/models/Workflow.ts";
import { WorkflowJobStatus } from "../../../shared/models/Workflow.ts";
import type { FC } from "react";
import useApplicationStore from "../../store/ApplicationStore.ts";
import Ansi from "ansi-to-react-18";

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
      {![
        WorkflowJobStatus.New,
        WorkflowJobStatus.InProgress,
        WorkflowJobStatus.Succeeded,
      ].includes(jobStatus) && (
        <>
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-200">
            Status Reason
          </h2>
          <MessageCard message={statusReason} />
        </>
      )}
      <LogViewer
        workflowType={workflowType.toUpperCase() as WorkflowType}
        appId={appId}
        job={job}
        runNumber={parseInt(runNumber, 10)}
      />
    </div>
  );
};

const MessageCard: FC<{ message: string }> = ({ message }) => {
  return (
    <div className="max-h-96 w-full rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
      <div className="h-fit max-h-64 w-full overflow-auto whitespace-break-spaces text-sm font-bold text-gray-700 dark:text-gray-400">
        <Ansi>{message}</Ansi>
      </div>
    </div>
  );
};
