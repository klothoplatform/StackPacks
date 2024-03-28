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
  Cancelled = "CANCELLED",
}

export enum WorkflowJobStatus {
  New = "NEW",
  Pending = "PENDING",
  InProgress = "IN_PROGRESS",
  Succeeded = "SUCCEEDED",
  Failed = "FAILED",
  Cancelled = "CANCELLED",
  Skipped = "SKIPPED",
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
  app_id?: string;
  jobs: WorkflowJob[];
}
