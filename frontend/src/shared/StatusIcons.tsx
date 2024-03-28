import { WorkflowJobStatus, WorkflowRunStatus } from "./models/Workflow.ts";
import type { ReactNode } from "react";
import React from "react";
import { CircleProgress } from "../components/icons/CircleProgress.tsx";
import {
  GoCheckCircle,
  GoCircle,
  GoClock,
  GoSkip,
  GoStop,
  GoXCircle,
} from "react-icons/go";

export const statusIcons: Record<
  WorkflowRunStatus | WorkflowJobStatus,
  {
    large: ReactNode;
    medium: ReactNode;
  }
> = {
  [WorkflowRunStatus.Pending]: {
    large: (
      <GoClock size={20} className={"text-yellow-600 dark:text-yellow-400"} />
    ),
    medium: (
      <GoClock size={16} className={"text-yellow-600 dark:text-yellow-400"} />
    ),
  },
  [WorkflowRunStatus.InProgress]: {
    large: (
      <CircleProgress
        size={22}
        className={"animate-spin text-yellow-600 dark:text-yellow-400"}
      />
    ),
    medium: (
      <CircleProgress
        size={18}
        className={"animate-spin text-yellow-600 dark:text-yellow-400"}
      />
    ),
  },
  [WorkflowRunStatus.Succeeded]: {
    large: (
      <GoCheckCircle
        size={22}
        className={"text-green-600 dark:text-green-500"}
      />
    ),
    medium: (
      <GoCheckCircle
        size={18}
        className={"text-green-600 dark:text-green-500"}
      />
    ),
  },
  [WorkflowRunStatus.Failed]: {
    large: <GoXCircle size={22} className={"text-red-600 dark:text-red-500"} />,
    medium: (
      <GoXCircle size={18} className={"text-red-600 dark:text-red-500"} />
    ),
  },
  [WorkflowRunStatus.Cancelled]: {
    large: <GoStop size={22} className={"text-gray-600 dark:text-gray-400"} />,
    medium: <GoStop size={18} className={"text-gray-600 dark:text-gray-400"} />,
  },
  [WorkflowRunStatus.New]: {
    large: (
      <GoCircle size={20} className={"text-gray-600 dark:text-gray-400"} />
    ),
    medium: (
      <GoCircle size={16} className={"text-gray-600 dark:text-gray-400"} />
    ),
  },
  [WorkflowJobStatus.Skipped]: {
    large: <GoSkip size={22} className={"text-gray-600 dark:text-gray-400"} />,
    medium: <GoSkip size={18} className={"text-gray-600 dark:text-gray-400"} />,
  },
};
