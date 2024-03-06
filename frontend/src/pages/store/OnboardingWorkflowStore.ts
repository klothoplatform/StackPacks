import type { StateCreator } from "zustand";
import type { ErrorStore } from "./ErrorStore";
import type { AuthStore } from "./AuthStore.ts";

export interface OnboardingWorkflowState {
  iamRoleArn?: string;
  externalId: string;
  selectedStackPacks: string[];
  region: string;
}

export interface OnboardingWorkflowStoreState {
  onboardingWorkflowState: OnboardingWorkflowState;
}

export interface OnboardingWorkflowStoreBase
  extends OnboardingWorkflowStoreState {
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
  },
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
