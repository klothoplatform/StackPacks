import { WorkflowPreviewer } from "../../WorkflowPreviewer.tsx";
import { Badge, Card, Table } from "flowbite-react";
import type {
  WorkflowRun,
  WorkflowRunStatus,
  WorkflowType,
} from "../../../shared/models/Workflow.ts";
import type { FC, PropsWithChildren, ReactNode } from "react";
import React, { useCallback, useEffect, useState } from "react";
import {
  getDurationString,
  getLocalTimezone,
  getTimeText,
} from "../../../shared/time-util.ts";
import { outlineBadge } from "../../../shared/custom-themes.ts";
import { titleCase } from "title-case";
import { useInterval } from "usehooks-ts";
import { useParams } from "react-router-dom";
import useApplicationStore from "../../store/ApplicationStore.ts";
import { UIError } from "../../../shared/errors.ts";
import { utcToZonedTime } from "date-fns-tz";
import type { JobGraph } from "../../../shared/job-graph.ts";
import { buildJobGraph } from "../../../shared/job-graph.ts";
import Linkify from "linkify-react";

export const RunOverviewPage = () => {
  const { runNumber, workflowType, appId } = useParams();
  const { addError, getWorkflowRun } = useApplicationStore();
  const [workflowRun, setWorkflowRun] = useState<WorkflowRun | null>(null);

  const [jobGraph, setJobGraph] = useState<JobGraph>({
    nodes: [],
    edges: [],
  });

  const refreshRun = useCallback(() => {
    (async () => {
      try {
        const run = await getWorkflowRun({
          runNumber: parseInt(runNumber),
          workflowType: workflowType.toUpperCase() as WorkflowType,
          appId: appId,
        });
        setWorkflowRun(run);
        setJobGraph(buildJobGraph(run.jobs));
      } catch (e: any) {
        addError(
          new UIError({
            errorId: "GetWorkflowRunError",
            message: "An error occurred while fetching workflow run.",
            cause: e,
          }),
        );
      }
    })();
  }, [addError, appId, getWorkflowRun, runNumber, workflowType]);

  useEffect(() => {
    refreshRun();
  }, [refreshRun]);

  const [interval, setInterval] = useState<number | null>(null);

  useEffect(() => {
    setInterval(workflowRun?.completed_at ? null : 20000);
  }, [workflowRun]);

  useInterval(() => {
    refreshRun();
  }, interval);

  if (!workflowRun) {
    return null;
  }

  return (
    <div className="flex flex-col gap-4 overflow-y-auto">
      <SummaryCard
        status={workflowRun.status}
        owningAppId={workflowRun.app_id}
        createdAt={utcToZonedTime(
          workflowRun.created_at,
          getLocalTimezone(),
        ).getTime()}
        completedAt={utcToZonedTime(
          workflowRun.completed_at,
          getLocalTimezone(),
        ).getTime()}
      />
      <WorkflowPreviewer jobGraph={jobGraph} />
      <h2 className="text-xl font-semibold">Outputs</h2>
      <WorkflowRunOutputs workflowRun={workflowRun} />
    </div>
  );
};

const SummaryCard: FC<{
  status: WorkflowRunStatus;
  owningAppId?: string;
  createdAt: number;
  completedAt?: number;
}> = ({ status, createdAt, completedAt, owningAppId }) => {
  console.log(completedAt, createdAt);
  return (
    <Card className="bg-gray-50 p-4 dark:bg-gray-900">
      <div className="flex gap-10">
        <SummaryItem label={`Triggered ${getTimeText(new Date(createdAt))}`}>
          {!!owningAppId && (
            <Badge theme={outlineBadge} color={"blue"} className="w-fit">
              {owningAppId}
            </Badge>
          )}
        </SummaryItem>
        <SummaryItem label={"Status"}>
          <span className={"text-lg font-medium"}>
            {titleCase(status.toLowerCase())}
          </span>
        </SummaryItem>
        <SummaryItem label={"Duration"}>
          <span className={"text-lg font-medium"}>
            {getDurationString(
              completedAt
                ? (completedAt - createdAt) / 1000
                : (Date.now() - createdAt) / 1000,
            )}
          </span>
        </SummaryItem>
      </div>
    </Card>
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
    <Card className="bg-gray-50 p-4 dark:bg-gray-900">
      {workflowRun.jobs.map((job, index) => (
        <div key={index}>
          <h3 className="text-lg font-medium">
            #{job.job_number}: {job.title}
          </h3>
          <Table>
            <Table.Head>
              <Table.HeadCell>Output Key</Table.HeadCell>
              <Table.HeadCell>Value</Table.HeadCell>
            </Table.Head>
            <Table.Body>
              {Object.entries(job.outputs).map(([key, value], index) => (
                <Table.Row key={index}>
                  <Table.Cell>{key}</Table.Cell>
                  <Table.Cell>
                    <Linkify>{value}</Linkify>
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>
        </div>
      ))}
    </Card>
  );
};
