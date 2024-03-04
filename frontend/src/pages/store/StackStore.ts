import type { StateCreator } from "zustand";
import type { ErrorStore } from "./ErrorStore";
import type { Stack } from "../../shared/models/Stack.ts";
import type { StackPack } from "../../shared/models/StackPack.ts";
import { getStack } from "../../api/GetStack.ts";
import type { AuthStore } from "./AuthStore.ts";
import { createStack } from "../../api/CreateStack.ts";
import { getStackPacks } from "../../api/GetStackPacks.ts";
import { installStack } from "../../api/InstallStack.ts";
import { tearDownStack } from "../../api/TearDownStack.ts";
import { updateStack } from "../../api/UpdateStack.ts";

export interface StackStoreState {
  userStack?: Stack;
  stackPacks: Map<string, StackPack>;
}

export interface StackStoreBase extends StackStoreState {
  getStack: () => Promise<Stack>;
  loadUserStack: () => Promise<Stack>;
  createStack: (stack: Partial<Stack>) => Promise<Stack>;
  updateStack: (stack: Partial<Stack>) => Promise<Stack>;
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
  loadUserStack: async () => {
    const userStack = await get().getStack();
    set({ userStack }, false, "loadUserStack");
    return userStack;
  },
  getStack: async () => {
    const idToken = await get().getIdToken();
    return await getStack(idToken);
  },
  createStack: async (stack: Partial<Stack>) => {
    const idToken = await get().getIdToken();
    return await createStack({ stack, idToken });
  },
  updateStack: async (stack: Partial<Stack>) => {
    const idToken = await get().getIdToken();
    return await updateStack({ stack, idToken });
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
