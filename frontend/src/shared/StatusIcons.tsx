import { WorkflowJobStatus, WorkflowRunStatus } from "./models/Workflow.ts";
import type { ReactNode } from "react";
import React from "react";
import {
  FaBan,
  FaRegCircle,
  FaRegCircleCheck,
  FaRegCircleXmark,
} from "react-icons/fa6";
import { CircleProgress } from "../components/icons/CircleProgress.tsx";
import { GoStop } from "react-icons/go";
import { AiOutlineClockCircle } from "react-icons/ai";

export const statusIcons: Record<
  WorkflowRunStatus | WorkflowJobStatus,
  {
    large: ReactNode;
    medium: ReactNode;
  }
> = {
  [WorkflowRunStatus.Pending]: {
    large: (
      <AiOutlineClockCircle
        size={24}
        className={"text-yellow-500 dark:text-yellow-400"}
      />
    ),
    medium: (
      <AiOutlineClockCircle
        size={20}
        className={"text-yellow-500 dark:text-yellow-400"}
      />
    ),
  },
  [WorkflowRunStatus.InProgress]: {
    large: (
      <CircleProgress
        size={22}
        className={"animate-spin text-yellow-500 dark:text-yellow-400"}
      />
    ),
    medium: (
      <CircleProgress
        size={18}
        className={"animate-spin text-yellow-500 dark:text-yellow-400"}
      />
    ),
  },
  [WorkflowRunStatus.Succeeded]: {
    large: (
      <FaRegCircleCheck
        size={22}
        className={"text-green-600 dark:text-green-500"}
      />
    ),
    medium: (
      <FaRegCircleCheck
        size={18}
        className={"text-green-600 dark:text-green-500"}
      />
    ),
  },
  [WorkflowRunStatus.Failed]: {
    large: (
      <FaRegCircleXmark
        size={22}
        className={"text-red-600 dark:text-red-500"}
      />
    ),
    medium: (
      <FaRegCircleXmark
        size={18}
        className={"text-red-600 dark:text-red-500"}
      />
    ),
  },
  [WorkflowRunStatus.Canceled]: {
    large: <GoStop size={22} className={"text-gray-600 dark:text-gray-400"} />,
    medium: <GoStop size={18} className={"text-gray-600 dark:text-gray-400"} />,
  },
  [WorkflowRunStatus.New]: {
    large: (
      <FaRegCircle size={20} className={"text-gray-600 dark:text-gray-400"} />
    ),
    medium: (
      <FaRegCircle size={16} className={"text-gray-600 dark:text-gray-400"} />
    ),
  },
  [WorkflowJobStatus.Skipped]: {
    large: <FaBan size={22} className={"text-gray-600 dark:text-gray-400"} />,
    medium: <FaBan size={18} className={"text-gray-600 dark:text-gray-400"} />,
  },
  [WorkflowJobStatus.Unknown]: {
    large: (
      <FaRegCircle size={20} className={"text-gray-600 dark:text-gray-400"} />
    ),
    medium: (
      <FaRegCircle size={16} className={"text-gray-600 dark:text-gray-400"} />
    ),
  },
};
