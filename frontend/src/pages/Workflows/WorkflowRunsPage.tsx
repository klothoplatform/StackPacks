import { Badge, Dropdown, Pagination, Table } from "flowbite-react";
import type { FC } from "react";
import React, { useCallback, useEffect, useState } from "react";
import type { WorkflowRunSummary } from "../../shared/models/Workflow.ts";
import {
  toWorkflowRunStatusString,
  WorkflowRunStatus,
  WorkflowType,
} from "../../shared/models/Workflow.ts";
import { Link, useParams, useSearchParams } from "react-router-dom";
import useApplicationStore from "../store/ApplicationStore.ts";
import { UIError } from "../../shared/errors.ts";
import { getEnumKeyByEnumValue } from "../../shared/object-util.ts";
import { outlineBadge } from "../../shared/custom-themes.ts";
import { titleCase } from "title-case";
import { GoCalendar, GoStopwatch } from "react-icons/go";
import { useInterval } from "usehooks-ts";
import { utcToZonedTime } from "date-fns-tz";
import { InlineDropdown } from "../../components/InlineDropdown.tsx";
import { statusIcons } from "../../shared/StatusIcons.tsx";
import {
  getDurationString,
  getLocalTimezone,
  getTimeText,
} from "../../shared/time-util.ts";

export const WorkflowRunsPage = () => {
  let { workflowType, appId } = useParams();

  if (!workflowType) {
    workflowType = WorkflowType.Any;
  }

  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunSummary[]>([]);

  const { getWorkflowRuns, addError, project } = useApplicationStore();

  const refreshRuns = useCallback(() => {
    (async () => {
      try {
        setWorkflowRuns(
          (
            await getWorkflowRuns({
              workflowType: workflowType as WorkflowType,
              appId: appId,
            })
          ).sort(
            (a, b) =>
              new Date(b.created_at).getTime() -
              new Date(a.created_at).getTime(),
          ),
        );
      } catch (e: any) {
        addError(
          new UIError({
            errorId: "GetWorkflowRunsError",
            message: "An error occurred while fetching workflow runs.",
            cause: e,
          }),
        );
      }
    })();
  }, [addError, appId, getWorkflowRuns, workflowType]);

  useEffect(() => {
    refreshRuns();
  }, [refreshRuns]);

  useInterval(() => {
    refreshRuns();
  }, 20000);

  return (
    <div className="flex size-full flex-col gap-4 overflow-auto pr-2">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-medium">
          {appId
            ? `${project.stack_packs[appId]?.display_name || appId}: `
            : ""}
          {workflowType === WorkflowType.Any
            ? "All Workflows"
            : titleCase(workflowType)}{" "}
        </h1>
      </div>
      <WorkflowRunsTable
        workflowRuns={workflowRuns}
        workflowType={workflowType}
        targetAppId={appId}
      />
    </div>
  );
};

const WorkflowRunsTable: FC<{
  workflowRuns: WorkflowRunSummary[];
  workflowType?: string;
  targetAppId?: string;
  pageSize?: number;
  activePage?: number;
}> = ({ workflowRuns, workflowType, targetAppId, pageSize, activePage }) => {
  pageSize = pageSize || 10;
  const { project } = useApplicationStore();
  const [currentPage, setCurrentPage] = useState(activePage || 1);

  const onPageChange = (page: number) => setCurrentPage(page);

  const [filteredWorkflowRuns, setFilteredWorkflowRuns] = useState<
    WorkflowRunSummary[][]
  >(splitArray(workflowRuns, pageSize));

  const [searchParams, setSearchParams] = useSearchParams();
  const selectedStatus = searchParams.get("status");

  useEffect(() => {
    const filtered = workflowRuns.filter((workflowRun) => {
      if (targetAppId && workflowRun.app_id !== targetAppId) {
        return false;
      }
      return !(selectedStatus && workflowRun.status !== selectedStatus);
    });
    setFilteredWorkflowRuns(splitArray(filtered, pageSize));
  }, [targetAppId, selectedStatus, workflowRuns, pageSize]);

  return (
    <div className={"flex flex-col gap-4"}>
      <Table>
        <Table.Head>
          <Table.HeadCell>
            <span className={"text-base font-medium"}>
              {(() => {
                const count = filteredWorkflowRuns?.reduce(
                  (acc, runs) => acc + runs.length,
                  0,
                );
                return `${count} workflow run${count === 1 ? "" : "s"}`;
              })()}
            </span>
          </Table.HeadCell>
          <Table.HeadCell></Table.HeadCell>
          <Table.HeadCell>
            <div className="flex w-full justify-end gap-2 font-normal">
              <InlineDropdown
                color={"light"}
                inline
                label={
                  targetAppId
                    ? project.stack_packs[targetAppId]?.display_name ||
                      targetAppId
                    : "All"
                }
                prefix={"Application"}
              >
                <Dropdown.Item
                  href={`/project/workflows${workflowType ? "/" + workflowType : ""}`}
                >
                  All
                </Dropdown.Item>
                {Object.values(project.stack_packs).map((app, index) => (
                  <Dropdown.Item
                    key={index}
                    href={`/project/apps/${app.app_id}/workflows${workflowType ? "/" + workflowType : ""}`}
                  >
                    {app.display_name}
                  </Dropdown.Item>
                ))}
              </InlineDropdown>
              <InlineDropdown
                inline
                prefix={"Status"}
                color={"light"}
                label={
                  selectedStatus
                    ? toWorkflowRunStatusString(
                        selectedStatus.toUpperCase() as WorkflowRunStatus,
                      )
                    : "All"
                }
              >
                <Dropdown.Item
                  onClick={() => {
                    setSearchParams({ status: "" });
                  }}
                >
                  All
                </Dropdown.Item>
                {Object.values(WorkflowRunStatus).map((status, index) => (
                  <Dropdown.Item
                    key={index}
                    onClick={() => {
                      setSearchParams({ status });
                    }}
                  >
                    {toWorkflowRunStatusString(status as WorkflowRunStatus)}
                  </Dropdown.Item>
                ))}
              </InlineDropdown>
            </div>
          </Table.HeadCell>
        </Table.Head>
        <Table.Body>
          {filteredWorkflowRuns[currentPage - 1]?.map((workflowRun, i) => {
            const appName =
              project.stack_packs[workflowRun.app_id]?.display_name ||
              workflowRun.app_id;
            return (
              <Table.Row
                key={i}
                className="bg-white dark:border-gray-700 dark:bg-gray-800"
              >
                <Table.Cell className="whitespace-nowrap font-medium text-gray-900 dark:text-white">
                  {
                    <SummaryCellContent
                      workflowRun={workflowRun}
                      appName={appName}
                    />
                  }
                </Table.Cell>
                <Table.Cell>
                  {!!workflowRun.app_id && (
                    <Badge
                      color={"blue"}
                      theme={outlineBadge}
                      className="size-fit"
                      title={workflowRun.app_id}
                      href={`/project/apps/${workflowRun.app_id.toLowerCase()}/configure`}
                    >
                      {appName}
                    </Badge>
                  )}
                </Table.Cell>
                <Table.Cell>
                  <ExecutionDetailsContent workflowRun={workflowRun} />
                </Table.Cell>
              </Table.Row>
            );
          })}
        </Table.Body>
      </Table>
      {filteredWorkflowRuns.length > 1 && (
        <div className="flex overflow-x-auto sm:justify-center">
          <Pagination
            layout="navigation"
            currentPage={currentPage}
            totalPages={filteredWorkflowRuns.length}
            onPageChange={onPageChange}
            showIcons
          />
        </div>
      )}
    </div>
  );
};

const ExecutionDetailsContent: FC<{ workflowRun: WorkflowRunSummary }> = ({
  workflowRun,
}) => {
  const createdAt = utcToZonedTime(
    new Date(workflowRun.created_at),
    Intl.DateTimeFormat().resolvedOptions().timeZone,
  );
  const completedAt = workflowRun.completed_at
    ? utcToZonedTime(new Date(workflowRun.completed_at), getLocalTimezone())
    : new Date();
  const [duration, setDuration] = useState(
    (completedAt.getTime() - createdAt.getTime()) / 1000,
  );

  const interval = workflowRun.completed_at ? null : 1000;
  useInterval(() => {
    setDuration((old) => old + 1);
  }, interval);

  return (
    <div className={"flex w-full justify-end text-gray-700 dark:text-gray-500"}>
      <div className={"flex w-32 flex-col gap-1"}>
        <div
          className={"flex gap-0.5"}
          title={`created at ${createdAt.toLocaleString()}`}
        >
          <GoCalendar size={16} />
          <span className="ml-1">{getTimeText(createdAt)}</span>
        </div>
        <div
          className={"flex gap-0.5"}
          title={`duration: ${getDurationString(duration)}`}
        >
          <GoStopwatch size={16} />

          <span className="ml-1">
            {workflowRun.completed_at
              ? getDurationString(duration)
              : toWorkflowRunStatusString(workflowRun.status)}
          </span>
        </div>
      </div>
    </div>
  );
};

const SummaryCellContent: FC<{
  workflowRun: WorkflowRunSummary;
  appName?: string;
}> = ({ workflowRun, appName }) => {
  const workflowType = getEnumKeyByEnumValue(
    WorkflowType,
    workflowRun.workflow_type,
  );

  const title = `${workflowType} ${appName || workflowRun.app_id || "all apps"}`;

  return (
    <div className="flex flex-col pl-6">
      <div className="flex items-center">
        <span className="absolute left-4">
          {statusIcons[workflowRun.status].large}
        </span>
        <Link
          to={`/project${workflowRun.app_id ? "/apps/" + workflowRun.app_id.toLowerCase() : ""}/workflows/${workflowRun.workflow_type.toLowerCase()}/runs/${workflowRun.run_number}`}
          className="text-base font-bold hover:text-blue-600 hover:underline dark:text-white dark:hover:text-blue-500"
        >
          {title}
        </Link>
      </div>
      <span className="text-xs text-gray-700 dark:text-gray-500">
        <span className={"font-bold"}>{title}</span> #{workflowRun.run_number}
      </span>
    </div>
  );
};

function splitArray<T>(array: T[], size: number): T[][] {
  let result = [];
  for (let i = 0; i < array.length; i += size) {
    result.push(array.slice(i, i + size));
  }
  return result;
}
