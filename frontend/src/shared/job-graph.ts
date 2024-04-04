import type { WorkflowJob } from "./models/Workflow.ts";
import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "@xyflow/react";
import { utcToZonedTime } from "date-fns-tz";
import { getLocalTimezone } from "./time-util.ts";

export interface JobGraph {
  nodes: Node[];
  edges: Edge[];
  maxOutgoingEdges: number;
}

export function buildJobGraph(jobs: WorkflowJob[]): JobGraph {
  const nodes =
    jobs.map((job) => {
      console.log(job);
      return {
        id: job.id,
        type: "workflowStep",
        data: {
          jobNumber: job.job_number,
          label: job.title,
          status: job.status,
          initiatedAt: utcToZonedTime(job.initiated_at, getLocalTimezone()),
          completedAt: job.completed_at
            ? utcToZonedTime(job.completed_at, getLocalTimezone())
            : null,
        },
      };
    }) ?? [];

  const edges =
    jobs
      .map((job) => {
        return job.dependencies.map((dep) => {
          return {
            id: `${job.id}-${dep}`,
            source: dep,
            target: job.id,
            type: "smoothstep",
          };
        });
      })
      .flat() ?? [];
  const outgoingEdgeCounts: Record<string, number> = {};
  edges.forEach((edge) => {
    if (outgoingEdgeCounts[edge.source]) {
      outgoingEdgeCounts[edge.source] += 1;
    } else {
      outgoingEdgeCounts[edge.source] = 1;
    }
  });
  const maxOutgoingEdges = Math.max(...Object.values(outgoingEdgeCounts));

  const initialGraph = { nodes, edges };

  return {
    maxOutgoingEdges,
    ...getLayoutedElements(initialGraph.nodes, initialGraph.edges),
  };
}

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 258;
const nodeHeight = 44;

const getLayoutedElements = (nodes, edges, direction = "LR") => {
  const isHorizontal = direction === "LR";
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? "left" : "top";
    node.sourcePosition = isHorizontal ? "right" : "bottom";

    // We are shifting the dagre node position (anchor=center center) to the top left
    // so it matches the React Flow node anchor point (top left).
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };

    return node;
  });

  return { nodes, edges };
};
