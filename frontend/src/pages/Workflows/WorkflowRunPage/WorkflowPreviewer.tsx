import type { FC } from "react";
import React, { useEffect, useMemo } from "react";
import {
  Controls,
  getIncomers,
  getOutgoers,
  Handle,
  Position,
  ReactFlow,
  useEdges,
  useNodes,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button, ButtonGroup, useThemeMode } from "flowbite-react";
import { HiMinus, HiPlus } from "react-icons/hi2";
import { MdFitScreen } from "react-icons/md";
import "../../../react-flow.scss";
import { useInterval } from "usehooks-ts";
import { WorkflowJobStatus } from "../../../shared/models/Workflow.ts";
import { statusIcons } from "../../../shared/StatusIcons.tsx";
import type { JobGraph } from "../../../shared/job-graph.ts";
import { getDurationString } from "../../../shared/time-util.ts";
import classNames from "classnames";
import { useNavigate } from "react-router-dom";

export const WorkflowPreviewer: FC<{
  jobGraph: JobGraph;
}> = ({ jobGraph: { nodes, edges, maxOutgoingEdges } }) => {
  const { mode } = useThemeMode();

  const nodeTypes = useMemo(() => ({ workflowStep: WorkflowStepNode }), []);

  const heightMap = {
    1: "h-[8rem]",
    2: "h-[16rem]",
    3: "h-[24rem]",
    4: "h-[32rem]",
  };
  const { fitView } = useReactFlow();
  const height = Math.min(4, maxOutgoingEdges);
  fitView({ nodes });
  return (
    <div
      className={classNames(
        heightMap[height] || "h-[8rem]",
        "max-h-[50%] min-h-[8rem] w-full rounded-lg border border-gray-200 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-900",
      )}
    >
      <ReactFlow
        colorMode={mode === "auto" ? "system" : mode}
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        proOptions={{
          hideAttribution: true,
        }}
        maxZoom={1}
        fitView
      >
        <Controls showInteractive={false} position={"bottom-right"} />
      </ReactFlow>
    </div>
  );
};

// TODO: finish implementing horizontal controls at some point -- they're nicer than xyflow's default controls
const HorizontalControls: FC = () => {
  const { mode } = useThemeMode();

  return (
    <Controls
      position={"bottom-right"}
      showFitView={false}
      showInteractive={false}
      showZoom={false}
    >
      <div
        className={
          "flex items-center gap-2 dark:fill-gray-200 dark:stroke-gray-200 dark:text-gray-200"
        }
      >
        <ButtonGroup>
          <Button size={"xs"} color={mode}>
            <HiMinus />
          </Button>
          <Button size={"xs"} color={mode}>
            <HiPlus />
          </Button>
        </ButtonGroup>
        <Button size={"xs"} color={mode}>
          <MdFitScreen />
        </Button>
      </div>
    </Controls>
  );
};

interface WorkflowStepNodeData {
  status: WorkflowJobStatus;
  jobNumber: number;
  label: string;
  initiatedAt: Date;
  completedAt: Date | null;
}

export function WorkflowStepNode({
  data,
  id,
}: {
  data: WorkflowStepNodeData;
  id: string;
}) {
  const [duration, setDuration] = React.useState<number | null>(
    data.initiatedAt && data.completedAt
      ? (data.completedAt.getTime() - data.initiatedAt.getTime()) / 1000
      : null,
  );

  const [interval, setInterval] = React.useState<number | null>(null);
  useEffect(() => {
    setInterval(
      data.completedAt || data.status !== WorkflowJobStatus.InProgress
        ? null
        : 1000,
    );
  }, [data.completedAt, data.status]);

  useInterval(() => {
    const latestTime = data.completedAt?.getTime() ?? Date.now();
    setDuration((duration) =>
      duration ? (latestTime - data.initiatedAt.getTime()) / 1000 : null,
    );
  }, interval);

  useEffect(() => {
    setDuration(
      data.initiatedAt
        ? ((data.completedAt?.getTime() ?? Date.now()) -
            data.initiatedAt.getTime()) /
            1000
        : null,
    );
  }, [data.initiatedAt, data.completedAt]);

  const nodes = useNodes();
  const edges = useEdges();
  const showLeftHandle = getIncomers({ id }, nodes, edges).length > 0;
  const showRightHandle = getOutgoers({ id }, nodes, edges).length > 0;
  const navigate = useNavigate();
  const icon = statusIcons[data.status]?.large;
  return (
    <>
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={false}
        className={classNames({
          hidden: !showLeftHandle,
        })}
      />
      <button
        className="flex h-[44px] w-[258px] cursor-pointer items-center justify-between gap-2 overflow-hidden text-ellipsis rounded-md border border-gray-300 bg-white px-2 text-sm  dark:border-gray-700 dark:bg-gray-800"
        onClick={() =>
          data.jobNumber ? navigate(`jobs/${data.jobNumber}`) : null
        }
      >
        <span className="flex w-fit items-center gap-2 overflow-hidden text-ellipsis">
          {icon} {data.label}
        </span>
        {!!duration && (
          <span className="whitespace-nowrap text-xs text-gray-500">
            {duration ? getDurationString(duration) : null}
          </span>
        )}
      </button>
      <Handle
        type="source"
        position={Position.Right}
        isConnectable={false}
        className={classNames({
          hidden: !showRightHandle,
        })}
      />
    </>
  );
}
