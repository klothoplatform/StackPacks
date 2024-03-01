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

export interface OnboardingWorkflowState {
  iamRoleArn?: string;
  externalId: string;
  selectedStackPacks: string[];
  region: string;
}

export interface OnboardingWorkflowStoreState {
  stack?: Stack;
  onboardingWorkflowState: OnboardingWorkflowState;
  stackPacks: Map<string, StackPack>;
}

export interface OnboardingWorkflowStoreBase
  extends OnboardingWorkflowStoreState {
  getStack: () => Promise<Stack>;
  createStack: (stack: Stack) => Promise<Stack>;
  updateStack: (stack: Partial<Stack>) => Promise<Stack>;
  getStackPacks: () => Promise<Map<string, StackPack>>;
  installStack: () => Promise<void>;
  tearDownStack: () => Promise<void>;
  resetOnboardingWorkflowState: (
    initialState?: Partial<OnboardingWorkflowState>,
  ) => void;
  updateOnboardingWorkflowState: (
    state: Partial<OnboardingWorkflowState>,
  ) => void;
}

const initialState: () => OnboardingWorkflowStoreState = () => ({
  onboardingWorkflowState: {
    externalId: crypto.randomUUID().toString(),
    selectedStackPacks: [],
    region: "",
    iamRoleArn: "arn:aws:iam::123456789012:role/role-remove-this-at-some-point",
  },
  stackPacks: new Map(),
});

export type OnboardingWorkflowStore = OnboardingWorkflowStoreBase &
  ErrorStore &
  AuthStore;

export const onboardingWorkflowStore: StateCreator<
  OnboardingWorkflowStore,
  [],
  [],
  OnboardingWorkflowStoreBase
> = (set: (state: object, replace?: boolean, id?: string) => any, get) => ({
  ...initialState(),
  resetOnboardingWorkflowState: (_initialState) =>
    set(
      { ...initialState(), ..._initialState },
      false,
      "resetOnboardingWorkflowState",
    ),
  getStack: async () => {
    const idToken = await get().getIdToken();
    return await getStack(idToken);
  },
  createStack: async (stack: Stack) => {
    const idToken = await get().getIdToken();
    return await createStack({ stack, idToken });
  },
  updateStack: async (stack: Partial<Stack>) => {
    const idToken = await get().getIdToken();
    return await updateStack({ stack, idToken });
  },
  getStackPacks: async () => {
    const idToken = await get().getIdToken();
    const currentStackPacks = get().stackPacks;
    if (currentStackPacks.size > 0) {
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
  updateOnboardingWorkflowState: (state: Partial<OnboardingWorkflowState>) => {
    set(
      {
        onboardingWorkflowState: {
          ...get().onboardingWorkflowState,
          ...state,
        },
      },
      false,
      "updateOnboardingWorkflowState",
    );
  },
});
