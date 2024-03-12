import type { StateCreator } from "zustand";
import type { ErrorStore } from "./ErrorStore";
import type {
  StackModification,
  UserStack,
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

export interface StackStoreState {
  userStack?: UserStack;
  userStackPolicy?: string;
  stackPacks: Map<string, AppTemplate>;
}

export interface StackStoreBase extends StackStoreState {
  getStack: () => Promise<UserStack>;
  getUserStack: (refresh?: boolean) => Promise<UserStack>;
  createOrUpdateStack: (
    stack: StackModification,
  ) => Promise<CreateStackResponse | UpdateStackResponse>;
  updateStack: (stack: StackModification) => Promise<UpdateStackResponse>;
  createStack: (stack: StackModification) => Promise<CreateStackResponse>;
  getStackPacks: (forceRefresh?: boolean) => Promise<Map<string, AppTemplate>>;
  installStack: () => Promise<void>;
  tearDownStack: () => Promise<void>;
  resetStackState: () => void;
  getAppTemplates: (
    appIds: string[],
    refresh?: boolean,
  ) => Promise<AppTemplate[]>;
}

const initialState: () => StackStoreState = () => ({
  stackPacks: new Map(),
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
    return await installStack(idToken);
  },
  tearDownStack: async () => {
    const idToken = await get().getIdToken();
    return await tearDownStack(idToken);
  },
  getAppTemplates: async (
    appIds: string[],
    refresh?: boolean,
  ): Promise<AppTemplate[]> => {
    const appTemplates = await get().getStackPacks(refresh);
    return appIds.map((id) => appTemplates.get(id));
  },
});
