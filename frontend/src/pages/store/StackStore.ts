import type { StateCreator } from "zustand";
import type { ErrorStore } from "./ErrorStore";
import type {
  Project,
  ProjectModification,
} from "../../shared/models/Project.ts";
import {
  AppDeploymentStatus,
  AppLifecycleStatus,
} from "../../shared/models/Project.ts";
import type { Stackpack } from "../../shared/models/Stackpack.ts";
import { resolveDefaultConfiguration } from "../../shared/models/Stackpack.ts";
import type { AuthStore } from "./AuthStore.ts";
import { getStackPacks } from "../../api/GetStackPacks.ts";
import { installProject } from "../../api/InstallProject.ts";
import { uninstallProject } from "../../api/UninstallProject.ts";
import type { UpdateProjectResponse } from "../../api/UpdateProject.ts";
import { updateProject } from "../../api/UpdateProject.ts";
import type { CreateStackResponse } from "../../api/CreateProject.ts";
import { createProject } from "../../api/CreateProject.ts";
import { merge } from "ts-deepmerge";
import type { UpdateAppResponse } from "../../api/UpdateApp.ts";
import { updateApp } from "../../api/UpdateApp.ts";
import { installApp } from "../../api/InstallApp.ts";
import { uninstallApp } from "../../api/UninstallApp.ts";
import { removeApp } from "../../api/RemoveApp.ts";
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
import { getProject } from "../../api/GetProject.ts";

export interface StackStoreState {
  project?: Project;
  userStackPolicy?: string;
  stackPacks: Map<string, Stackpack>;
  latestDeploymentIds: Map<string, string>;
}

export interface StackStoreBase extends StackStoreState {
  createProject: (stack: ProjectModification) => Promise<CreateStackResponse>;
  createOrUpdateProject: (
    stack: ProjectModification,
  ) => Promise<CreateStackResponse | UpdateProjectResponse>;
  subscribeToLogStream: (
    request: Omit<LogSubscriptionRequest, "idToken">,
  ) => Promise<void>;
  getProject: (refresh?: boolean) => Promise<Project>;
  getStackPacks: (forceRefresh?: boolean) => Promise<Map<string, Stackpack>>;
  getWorkflowRun: (
    request: Omit<GetWorkflowRunRequest, "idToken">,
  ) => Promise<WorkflowRun>;
  getWorkflowRuns: (
    request: Omit<GetWorkflowRunsRequest, "idToken">,
  ) => Promise<WorkflowRunSummary[]>;
  installApp: (appId: string) => Promise<string>;
  installProject: () => Promise<string>;
  removeApp: (appId: string) => Promise<void>;
  resetStackState: () => void;
  uninstallApp: (appId: string) => Promise<string>;
  uninstallProject: () => Promise<string>;
  updateApp: (
    appId: string,
    configuration: Record<string, any>,
  ) => Promise<UpdateAppResponse>;
  updateProject: (stack: ProjectModification) => Promise<UpdateProjectResponse>;
}

const initialState: () => StackStoreState = () => ({
  stackPacks: new Map(),
  latestDeploymentIds: new Map(),
});

export type StackStore = StackStoreBase & ErrorStore & AuthStore;

export const stackStore: StateCreator<StackStore, [], [], StackStoreBase> = (
  set: (state: object, replace?: boolean, id?: string) => any,
  get,
) => ({
  ...initialState(),
  resetStackState: () => set(initialState(), false, "resetStackState"),
  getProject: async (refresh?: boolean) => {
    let project = get().project;
    if (refresh || !project) {
      const idToken = await get().getIdToken();
      project = await getProject(idToken);
    }
    set({ project }, false, "getProject");
    return project;
  },
  createProject: async (stack: Partial<Project>) => {
    const idToken = await get().getIdToken();

    const response = await createProject({ stack, idToken });
    set(
      {
        userStack: response.stack,
        userStackPolicy: response.policy,
      },
      false,
      "createProject",
    );
    return response;
  },
  createOrUpdateProject: async (stack: ProjectModification) => {
    const appTemplates = await get().getStackPacks();
    const defaultConfiguration = Object.fromEntries(
      Object.keys(stack.configuration ?? {}).map((appId) => [
        appId,
        resolveDefaultConfiguration(appTemplates.get(appId)),
      ]),
    );

    // handle the case where the user has a stack and is updating it
    const userStack = await get().getProject();
    if (userStack) {
      stack = {
        ...stack,
        configuration: { ...stack.configuration },
      };
      Object.entries(stack.configuration).forEach(([key, value]) => {
        if (value === undefined || Object.keys(value).length === 0) {
          stack.configuration[key] =
            userStack.stack_packs[key]?.configuration ??
            defaultConfiguration[key] ??
            stack.configuration[key];
        }
      });
      return await get().updateProject(stack);
    }

    // handle the case where the user does not have a stack and is creating one
    stack = { ...stack };
    stack.configuration = merge(defaultConfiguration, stack.configuration);

    return await get().createProject(stack);
  },
  updateProject: async (stack: Partial<Project>) => {
    const idToken = await get().getIdToken();
    const response = await updateProject({ stack, idToken });
    set(
      {
        userStack: response.stack,
        userStackPolicy: response.policy,
      },
      false,
      "updateStack",
    );
    return response;
  },
  getStackPacks: async (forceRefresh?: boolean) => {
    const currentStackPacks = get().stackPacks;
    if (!forceRefresh && currentStackPacks.size > 0) {
      return currentStackPacks;
    }
    const idToken = await get().getIdToken();
    const updatedStackPacks = await getStackPacks(idToken);
    set(
      {
        stackPacks: updatedStackPacks,
      },
      false,
      "getStackPacks",
    );
    return updatedStackPacks;
  },
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
            Object.keys(userStack?.stack_packs ?? {}).map((appId) => [
              appId,
              {
                ...userStack.stack_packs[appId],
                status: AppDeploymentStatus.Pending,
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
                status: AppLifecycleStatus.Uninstalling,
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
              status: AppDeploymentStatus.Pending,
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
              status: AppLifecycleStatus.Uninstalling,
            },
          },
        },
      },
      false,
      "tearDownApp:init",
    );
    const idToken = await get().getIdToken();
    const deploymentId = await uninstallApp({ idToken, appId });
    set(
      {
        latestDeploymentIds: new Map([[appId, deploymentId]]),
      },
      false,
      "tearDownApp:success",
    );
    return deploymentId;
  },
  updateApp: async (appId: string, configuration: Record<string, any>) => {
    const idToken = await get().getIdToken();
    const response = await updateApp({ appId, configuration, idToken });
    set(
      {
        userStack: response.stack,
        userStackPolicy: response.policy,
      },
      false,
      "updateApp",
    );
    return response;
  },
  removeApp: async (appId: string) => {
    const idToken = await get().getIdToken();
    const response = await removeApp({ idToken, appId });
    set(
      {
        userStack: response.stack,
        userStackPolicy: response.policy,
      },
      false,
      "removeApp",
    );
  },
  getWorkflowRun: async ({
    workflowType,
    runNumber,
    appId,
  }: GetWorkflowRunRequest) => {
    const idToken = await get().getIdToken();
    return await getWorkflowRun({ idToken, workflowType, runNumber, appId });
  },
  getWorkflowRuns: async ({ workflowType, appId }: GetWorkflowRunsRequest) => {
    const idToken = await get().getIdToken();
    return await getWorkflowRuns({ idToken, workflowType, appId });
  },
});
