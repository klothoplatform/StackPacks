export enum WorkflowType {
  Deploy = "DEPLOY",
  Destroy = "DESTROY",
  Any = "any",
}

export enum WorkflowJobType {
  Deploy = "DEPLOY",
  Destroy = "DESTROY",
  Any = "any",
}

export enum WorkflowRunStatus {
  New = "NEW",
  Pending = "PENDING",
  InProgress = "IN_PROGRESS",
  Succeeded = "SUCCEEDED",
  Failed = "FAILED",
  Canceled = "CANCELED",
  Unknown = "UNKNOWN",
}

export enum WorkflowJobStatus {
  New = "NEW",
  Pending = "PENDING",
  InProgress = "IN_PROGRESS",
  Succeeded = "SUCCEEDED",
  Failed = "FAILED",
  Canceled = "CANCELED",
  Skipped = "SKIPPED",
  Unknown = "UNKNOWN",
}

const workflowRunStatuses: Record<WorkflowRunStatus, string> = {
  [WorkflowRunStatus.New]: "New",
  [WorkflowRunStatus.Pending]: "Pending",
  [WorkflowRunStatus.InProgress]: "In Progress",
  [WorkflowRunStatus.Succeeded]: "Succeeded",
  [WorkflowRunStatus.Failed]: "Failed",
  [WorkflowRunStatus.Canceled]: "Canceled",
  [WorkflowRunStatus.Unknown]: "Unknown",
};

const workflowJobStatuses: Record<WorkflowJobStatus, string> = {
  [WorkflowJobStatus.New]: "New",
  [WorkflowJobStatus.Pending]: "Pending",
  [WorkflowJobStatus.InProgress]: "In Progress",
  [WorkflowJobStatus.Succeeded]: "Succeeded",
  [WorkflowJobStatus.Failed]: "Failed",
  [WorkflowJobStatus.Skipped]: "Skipped",
  [WorkflowJobStatus.Canceled]: "Canceled",
  [WorkflowJobStatus.Unknown]: "Unknown",
};

export function toWorkflowRunStatusString(status: WorkflowRunStatus) {
  return workflowRunStatuses[status] || WorkflowRunStatus.Unknown;
}

export function toWorkflowJobStatusString(status: WorkflowJobStatus) {
  return workflowJobStatuses[status] || WorkflowJobStatus.Unknown;
}

export interface WorkflowRunSummary {
  id: string;
  run_number: number;
  workflow_type: WorkflowType;
  created_at: number;
  initiated_by: string;
  initiated_at?: number;
  completed_at?: number;
  status: WorkflowRunStatus;
  app_id?: string;
}

export interface WorkflowJob {
  id: string;
  job_number: number;
  status: WorkflowJobStatus;
  job_type: WorkflowJobType;
  title: string;
  initiated_at?: number;
  completed_at?: number;
  status_reason: string;
  dependencies: string[];
  outputs: Record<string, string>;
}

export interface WorkflowRun {
  id: string;
  run_number: number;
  project_id: string;
  created_at: number;
  workflow_type: WorkflowType;
  initiated_by: string;
  initiated_at?: number;
  completed_at?: number;
  status: WorkflowRunStatus;
  status_reason: string;
  app_id?: string;
  jobs: WorkflowJob[];
}
