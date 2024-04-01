import { WorkflowPreviewer } from "../../WorkflowPreviewer.tsx";
import { Badge, Table } from "flowbite-react";
import type {
  WorkflowRun,
  WorkflowType,
} from "../../../shared/models/Workflow.ts";
import { WorkflowRunStatus } from "../../../shared/models/Workflow.ts";
import { toWorkflowRunStatusString } from "../../../shared/models/Workflow.ts";
import type { FC, PropsWithChildren, ReactNode } from "react";
import React, { useCallback, useEffect, useState } from "react";
import {
  getDurationString,
  getLocalTimezone,
  getTimeText,
} from "../../../shared/time-util.ts";
import { altTable, outlineBadge } from "../../../shared/custom-themes.ts";
import { useParams } from "react-router-dom";
import useApplicationStore from "../../store/ApplicationStore.ts";
import { utcToZonedTime } from "date-fns-tz";
import type { JobGraph } from "../../../shared/job-graph.ts";
import { buildJobGraph } from "../../../shared/job-graph.ts";
import Linkify from "linkify-react";
import { useInterval } from "usehooks-ts";
import { StatusReasonCard } from "../../../components/StatusReasonCard.tsx";

export const RunOverviewPage = () => {
  const { runNumber, workflowType, appId } = useParams();
  const { getWorkflowRun, workflowRun, project } = useApplicationStore();

  const [jobGraph, setJobGraph] = useState<JobGraph>({
    nodes: [],
    edges: [],
  });

  useEffect(() => {
    setJobGraph(buildJobGraph(workflowRun.jobs));
  }, [workflowRun]);

  const refreshRun = useCallback(() => {
    (async () => {
      try {
        await getWorkflowRun({
          runNumber: parseInt(runNumber, 10),
          workflowType: workflowType.toUpperCase() as WorkflowType,
          appId: appId,
        });
      } catch (e: any) {
        console.error(e);
      }
    })();
  }, [appId, getWorkflowRun, runNumber, workflowType]);

  useEffect(() => {
    refreshRun();
  }, [refreshRun]);

  if (!workflowRun) {
    return null;
  }

  return (
    <div className="flex flex-col gap-4 overflow-y-auto">
      <SummaryCard
        status={workflowRun.status}
        appName={
          project.stack_packs[workflowRun.app_id]?.display_name ||
          workflowRun.app_id
        }
        createdAt={utcToZonedTime(
          workflowRun.created_at,
          getLocalTimezone(),
        ).getTime()}
        completedAt={
          workflowRun.completed_at &&
          utcToZonedTime(workflowRun.completed_at, getLocalTimezone()).getTime()
        }
        initiatedAt={
          workflowRun.initiated_at &&
          utcToZonedTime(workflowRun.initiated_at, getLocalTimezone()).getTime()
        }
      />
      <WorkflowPreviewer jobGraph={jobGraph} />
      <h2 className="text-xl font-semibold">Outputs</h2>
      <WorkflowRunOutputs workflowRun={workflowRun} />
      {![
        WorkflowRunStatus.New,
        WorkflowRunStatus.InProgress,
        WorkflowRunStatus.Succeeded,
      ].includes(workflowRun.status) && (
        <>
          <h2 className="text-xl font-semibold">Status Reason</h2>
          <StatusReasonCard message={workflowRun.status_reason} />
        </>
      )}
    </div>
  );
};

function resolveDuration(
  initiatedAt: number | undefined,
  completedAt: number | undefined,
) {
  const latestTime = completedAt ?? Date.now();
  return initiatedAt ? (latestTime - initiatedAt) / 1000 : null;
}

const SummaryCard: FC<{
  status: WorkflowRunStatus;
  appName?: string;
  createdAt: number;
  initiatedAt?: number;
  completedAt?: number;
}> = ({ status, createdAt, initiatedAt, completedAt, appName }) => {
  const [duration, setDuration] = useState<number>(
    resolveDuration(initiatedAt, completedAt),
  );
  const [tickInterval, setTickInterval] = useState<number>(null);

  useEffect(() => {
    if (initiatedAt && !completedAt) {
      setTickInterval(1000);
      setDuration((Date.now() - initiatedAt) / 1000);
    }
  }, [initiatedAt, completedAt]);

  useInterval(() => {
    setDuration(resolveDuration(initiatedAt, completedAt));
  }, tickInterval);

  return (
    <div className="h-fit w-full rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
      <div className="flex gap-10">
        <SummaryItem label={`Triggered ${getTimeText(new Date(createdAt))}`}>
          {!!appName && (
            <Badge theme={outlineBadge} color={"blue"} className="w-fit">
              {appName}
            </Badge>
          )}
        </SummaryItem>
        <SummaryItem label={"Status"}>
          <span className={"text-lg font-medium"}>
            {toWorkflowRunStatusString(status)}
          </span>
        </SummaryItem>
        <SummaryItem label={"Duration"}>
          <span className={"text-lg font-medium"}>
            {duration
              ? getDurationString(
                  completedAt
                    ? (completedAt - createdAt) / 1000
                    : (Date.now() - createdAt) / 1000,
                )
              : "--"}
          </span>
        </SummaryItem>
      </div>
    </div>
  );
};

const SummaryItem: FC<
  PropsWithChildren<{
    label: string | ReactNode;
  }>
> = (props) => {
  return (
    <div className="flex flex-col gap-2">
      <span className={"text-xs font-medium text-gray-700 dark:text-gray-400"}>
        {props.label}
      </span>
      {props.children}
    </div>
  );
};

const WorkflowRunOutputs: FC<{
  workflowRun: WorkflowRun;
}> = ({ workflowRun }) => {
  return (
    <div className="h-fit w-full rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
      <Table theme={altTable}>
        <Table.Head>
          <Table.HeadCell>Job</Table.HeadCell>
          <Table.HeadCell>Output Key</Table.HeadCell>
          <Table.HeadCell>Value</Table.HeadCell>
        </Table.Head>

        <Table.Body>
          {workflowRun.jobs.map(
            (job, index) =>
              Object.keys(job.outputs ?? {}).keys() && (
                <React.Fragment key={index}>
                  {Object.entries(job.outputs).map(([key, value], index) => (
                    <Table.Row key={index}>
                      <Table.Cell>
                        #{job.job_number}: {job.title}
                      </Table.Cell>
                      <Table.Cell>{key}</Table.Cell>
                      <Table.Cell>
                        <Linkify
                          options={{
                            attributes: {
                              target: "_blank",
                              rel: "noopener noreferrer",
                            },
                            className: "text-blue-600",
                          }}
                        >
                          {value}
                        </Linkify>
                      </Table.Cell>
                    </Table.Row>
                  ))}
                </React.Fragment>
              ),
          )}
        </Table.Body>
      </Table>
    </div>
  );
};
