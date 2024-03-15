import type { StateCreator } from "zustand";
import type { ErrorStore } from "./ErrorStore";
import type {
  StackModification,
  UserStack,
} from "../../shared/models/UserStack.ts";
import {
  AppDeploymentStatus,
  AppLifecycleStatus,
} from "../../shared/models/UserStack.ts";
import type { AppTemplate } from "../../shared/models/AppTemplate.ts";
import { resolveDefaultConfiguration } from "../../shared/models/AppTemplate.ts";
import { getStack } from "../../api/GetStack.ts";
import type { AuthStore } from "./AuthStore.ts";
import { getStackPacks } from "../../api/GetStackPacks.ts";
import { installStack } from "../../api/InstallStack.ts";
import { tearDownStack } from "../../api/TearDownStack.ts";
import type { UpdateStackResponse } from "../../api/UpdateStack.ts";
import { updateStack } from "../../api/UpdateStack.ts";
import type { CreateStackResponse } from "../../api/CreateStack.ts";
import { createStack } from "../../api/CreateStack.ts";
import { merge } from "ts-deepmerge";
import type { UpdateAppResponse } from "../../api/UpdateApp.ts";
import { updateApp } from "../../api/UpdateApp.ts";
import { installApp } from "../../api/InstallApp.ts";
import { tearDownApp } from "../../api/TearDownApp.ts";
import { removeApp } from "../../api/RemoveApp.ts";
import type { LogStreamListener } from "../../api/DeployLogs.ts";
import { subscribeToLogStream } from "../../api/DeployLogs.ts";
import { getDeployments } from "../../api/GetDeployments.ts";

export interface StackStoreState {
  userStack?: UserStack;
  userStackPolicy?: string;
  stackPacks: Map<string, AppTemplate>;
  latestDeploymentIds: Map<string, string>;
}

export interface StackStoreBase extends StackStoreState {
  createStack: (stack: StackModification) => Promise<CreateStackResponse>;
  createOrUpdateStack: (
    stack: StackModification,
  ) => Promise<CreateStackResponse | UpdateStackResponse>;
  subscribeToLogStream: (
    deploy_id: string,
    app_id: string,
    listener: LogStreamListener,
    controller?: AbortController,
  ) => Promise<void>;
  getAppTemplates: (
    appIds: string[],
    refresh?: boolean,
  ) => Promise<AppTemplate[]>;
  getDeployments: () => Promise<any>;
  getStack: () => Promise<UserStack>;
  getStackPacks: (forceRefresh?: boolean) => Promise<Map<string, AppTemplate>>;
  getUserStack: (refresh?: boolean) => Promise<UserStack>;
  installApp: (appId: string) => Promise<string>;
  installStack: () => Promise<string>;
  removeApp: (appId: string) => Promise<void>;
  resetStackState: () => void;
  tearDownApp: (appId: string) => Promise<string>;
  tearDownStack: () => Promise<string>;
  updateApp: (
    appId: string,
    configuration: Record<string, any>,
  ) => Promise<UpdateAppResponse>;
  updateStack: (stack: StackModification) => Promise<UpdateStackResponse>;
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
  getUserStack: async (refresh?: boolean) => {
    let userStack = get().userStack;
    if (refresh || !userStack) {
      userStack = await get().getStack();
    }
    set({ userStack }, false, "getUserStack");
    return userStack;
  },
  getStack: async () => {
    const idToken = await get().getIdToken();
    return await getStack(idToken);
  },
  createStack: async (stack: Partial<UserStack>) => {
    const idToken = await get().getIdToken();

    const response = await createStack({ stack, idToken });
    set(
      {
        userStack: response.stack,
        userStackPolicy: response.policy,
      },
      false,
      "createStack",
    );
    return response;
  },
  createOrUpdateStack: async (stack: StackModification) => {
    const appTemplates = await get().getStackPacks();
    const defaultConfiguration = Object.fromEntries(
      Object.keys(stack.configuration ?? {}).map((appId) => [
        appId,
        resolveDefaultConfiguration(appTemplates.get(appId)),
      ]),
    );

    // handle the case where the user has a stack and is updating it
    const userStack = await get().getUserStack();
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
      return await get().updateStack(stack);
    }

    // handle the case where the user does not have a stack and is creating one
    stack = { ...stack };
    stack.configuration = merge(defaultConfiguration, stack.configuration);

    return await get().createStack(stack);
  },
  updateStack: async (stack: Partial<UserStack>) => {
    const idToken = await get().getIdToken();
    const response = await updateStack({ stack, idToken });
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
  installStack: async () => {
    const idToken = await get().getIdToken();
    const response = await installStack(idToken);
    const userStack = get().userStack;
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
  tearDownStack: async () => {
    const idToken = await get().getIdToken();
    const deploymentId = await tearDownStack(idToken);
    set(
      {
        latestDeploymentIds: new Map(
          Object.keys(get().userStack?.stack_packs ?? {}).map((appId) => [
            appId,
            deploymentId,
          ]),
        ),
        userStack: {
          ...get().userStack,
          stack_packs: Object.fromEntries(
            Object.keys(get().userStack?.stack_packs ?? {}).map((appId) => [
              appId,
              {
                ...get().userStack?.stack_packs[appId],
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
  subscribeToLogStream: async (deploy_id, app_id, listener, controller) => {
    const idToken = await get().getIdToken();
    return subscribeToLogStream({
      idToken,
      deploymentId: deploy_id,
      appId: app_id,
      listener,
      controller,
    });
  },
  getAppTemplates: async (
    appIds: string[],
    refresh?: boolean,
  ): Promise<AppTemplate[]> => {
    const appTemplates = await get().getStackPacks(refresh);
    return appIds.map((id) => appTemplates.get(id));
  },
  installApp: async (appId: string) => {
    const userStack = await get().getUserStack();
    set(
      {
        userStack: {
          ...get().userStack,
          stack_packs: {
            ...get().userStack?.stack_packs,
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
  tearDownApp: async (appId: string) => {
    set(
      {
        userStack: {
          ...get().userStack,
          stack_packs: {
            ...get().userStack?.stack_packs,
            [appId]: {
              ...get().userStack?.stack_packs[appId],
              status: AppLifecycleStatus.Uninstalling,
            },
          },
        },
      },
      false,
      "tearDownApp:init",
    );
    const idToken = await get().getIdToken();
    const deploymentId = await tearDownApp({ idToken, appId });
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
  getDeployments: async () => {
    const idToken = await get().getIdToken();
    return await getDeployments(idToken);
  },
});
