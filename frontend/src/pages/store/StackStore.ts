import type { StateCreator } from "zustand";
import type { ErrorStore } from "./ErrorStore";
import type { Stack } from "../../shared/models/Stack.ts";
import { resolveDefaultConfigurations } from "../../shared/models/Stack.ts";
import type { StackPack } from "../../shared/models/StackPack.ts";
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
  userStack?: Stack;
  userStackPolicy?: string;
  stackPacks: Map<string, StackPack>;
}

export interface StackStoreBase extends StackStoreState {
  getStack: () => Promise<Stack>;
  getUserStack: (refresh?: boolean) => Promise<Stack>;
  createOrUpdateStack: (
    stack?: Partial<Stack>,
  ) => Promise<CreateStackResponse | UpdateStackResponse>;
  updateStack: (stack: Partial<Stack>) => Promise<UpdateStackResponse>;
  createStack: (stack: Partial<Stack>) => Promise<CreateStackResponse>;
  getStackPacks: (forceRefresh?: boolean) => Promise<Map<string, StackPack>>;
  installStack: () => Promise<void>;
  tearDownStack: () => Promise<void>;
  resetStackState: () => void;
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
  createStack: async (stack: Partial<Stack>) => {
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
  createOrUpdateStack: async (stack: Partial<Stack>) => {
    const defaultConfiguration = resolveDefaultConfigurations(
      stack as Stack,
      await get().getStackPacks(),
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
            userStack.configuration[key] ??
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
  updateStack: async (stack: Partial<Stack>) => {
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
    const idToken = await get().getIdToken();
    const currentStackPacks = get().stackPacks;
    if (!forceRefresh && currentStackPacks.size > 0) {
      return currentStackPacks;
    }
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
});
