import type { StateCreator } from "zustand";
import { AppLifecycleStatus } from "../../shared/models/Project.ts";
import { installProject } from "../../api/InstallProject.ts";
import { uninstallProject } from "../../api/UninstallProject.ts";
import { installApp } from "../../api/InstallApp.ts";
import { uninstallApp } from "../../api/UninstallApp.ts";
import type { LogSubscriptionRequest } from "../../api/SubscribeToLogStream.ts";
import { subscribeToLogStream } from "../../api/SubscribeToLogStream.ts";
import type { GetWorkflowRunRequest } from "../../api/GetWorkflowRun.ts";
import { getWorkflowRun } from "../../api/GetWorkflowRun.ts";
import type {
  WorkflowRun,
  WorkflowRunSummary,
} from "../../shared/models/Workflow.ts";
import type { GetWorkflowRunsRequest } from "../../api/GetWorkflowRuns.ts";
import { getWorkflowRuns } from "../../api/GetWorkflowRuns.ts";
import type { ProjectStore } from "./ProjectStore.ts";

export interface WorkflowStoreState {
  workflowRun?: WorkflowRun;
  workflowRuns: WorkflowRunSummary[];
}

export interface WorkflowStoreBase extends WorkflowStoreState {
  subscribeToLogStream: (
    request: Omit<LogSubscriptionRequest, "idToken">,
  ) => Promise<void>;
  getWorkflowRun: (
    request: Omit<GetWorkflowRunRequest, "idToken">,
  ) => Promise<WorkflowRun>;
  getWorkflowRuns: (
    request: Omit<GetWorkflowRunsRequest, "idToken">,
  ) => Promise<WorkflowRunSummary[]>;
  installApp: (appId: string) => Promise<WorkflowRunSummary>;
  installProject: () => Promise<WorkflowRunSummary>;
  uninstallApp: (appId: string) => Promise<WorkflowRunSummary>;
  uninstallProject: () => Promise<WorkflowRunSummary>;
  resetWorkflowState: () => void;
}

const initialState: () => WorkflowStoreState = () => ({
  workflowRuns: [],
  workflowRun: undefined,
});

export type WorkflowStore = WorkflowStoreBase & ProjectStore;

export const workflowStore: StateCreator<
  WorkflowStore,
  [],
  [],
  WorkflowStoreBase
> = (set: (state: object, replace?: boolean, id?: string) => any, get) => ({
  ...initialState(),
  resetWorkflowState: () => set(initialState(), false, "resetWorkflowState"),
  installProject: async () => {
    const idToken = await get().getIdToken();
    const response = await installProject(idToken);
    const userStack = get().project;
    set(
      {
        latestDeploymentIds: new Map(
          Object.keys(userStack?.stack_packs ?? {}).map((appId) => [
            appId,
            response,
          ]),
        ),
        userStack: {
          ...userStack,
          stack_packs: Object.fromEntries(
            Object.entries(userStack?.stack_packs ?? {}).map(([appId, app]) => [
              appId,
              {
                ...app,
                status: AppLifecycleStatus.Pending,
              },
            ]),
          ),
        },
      },
      false,
      "installStack:init",
    );
    return response;
  },
  uninstallProject: async () => {
    const idToken = await get().getIdToken();
    const deploymentId = await uninstallProject(idToken);
    set(
      {
        latestDeploymentIds: new Map(
          Object.keys(get().project?.stack_packs ?? {}).map((appId) => [
            appId,
            deploymentId,
          ]),
        ),
        userStack: {
          ...get().project,
          stack_packs: Object.fromEntries(
            Object.keys(get().project?.stack_packs ?? {}).map((appId) => [
              appId,
              {
                ...get().project?.stack_packs[appId],
                status: AppLifecycleStatus.Pending,
              },
            ]),
          ),
        },
      },
      false,
      "tearDownStack:init",
    );
    return deploymentId;
  },
  subscribeToLogStream: async ({
    workflowType,
    targetedAppId,
    runNumber,
    jobNumber,
    listener,
    controller,
  }: LogSubscriptionRequest) => {
    const idToken = await get().getIdToken();
    return subscribeToLogStream({
      workflowType,
      targetedAppId,
      idToken,
      runNumber,
      jobNumber,
      listener,
      controller,
    });
  },
  installApp: async (appId: string) => {
    const userStack = await get().getProject();
    set(
      {
        userStack: {
          ...get().project,
          stack_packs: {
            ...get().project?.stack_packs,
            [appId]: {
              ...userStack.stack_packs[appId],
              status: AppLifecycleStatus.Pending,
            },
          },
        },
      },
      false,
      "installApp:init",
    );
    const idToken = await get().getIdToken();
    const deploymentId = await installApp({ idToken, appId });
    set(
      {
        latestDeploymentIds: new Map([[appId, deploymentId]]),
      },
      false,
      "installApp:success",
    );
    return deploymentId;
  },
  uninstallApp: async (appId: string) => {
    set(
      {
        userStack: {
          ...get().project,
          stack_packs: {
            ...get().project?.stack_packs,
            [appId]: {
              ...get().project?.stack_packs[appId],
              status: AppLifecycleStatus.Pending,
            },
          },
        },
      },
      false,
      "uninstallApp:init",
    );
    const idToken = await get().getIdToken();
    const deploymentId = await uninstallApp({ idToken, appId });
    set(
      {
        latestDeploymentIds: new Map([[appId, deploymentId]]),
      },
      false,
      "uninstallApp:success",
    );
    return deploymentId;
  },
  getWorkflowRun: async ({
    workflowType,
    runNumber,
    appId,
  }: GetWorkflowRunRequest) => {
    const idToken = await get().getIdToken();
    const run = await getWorkflowRun({
      idToken,
      workflowType,
      runNumber,
      appId,
    });
    set({ workflowRun: run }, false, "getWorkflowRun");
    return run;
  },
  getWorkflowRuns: async ({ workflowType, appId }: GetWorkflowRunsRequest) => {
    const idToken = await get().getIdToken();
    const runs = await getWorkflowRuns({ idToken, workflowType, appId });
    set({ workflowRuns: runs }, false, "getWorkflowRuns");
    return runs;
  },
});
