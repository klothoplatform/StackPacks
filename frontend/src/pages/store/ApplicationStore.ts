import type { StoreApi, UseBoundStore } from "zustand";
import { createWithEqualityFn } from "zustand/traditional";
import { shallow } from "zustand/shallow";
import { authStore } from "./AuthStore";
import { devtools, persist } from "zustand/middleware";
import { errorStore } from "./ErrorStore";
import type { OnboardingWorkflowStore } from "./OnboardingWorkflowStore.ts";
import { onboardingWorkflowStore } from "./OnboardingWorkflowStore.ts";
import type { ProjectStore } from "./ProjectStore.ts";
import { projectStore } from "./ProjectStore.ts";
import type { WorkflowStore } from "./WorkflowStore.ts";
import { workflowStore } from "./WorkflowStore.ts";

type WithSelectors<S> = S extends {
  getState: () => infer T;
}
  ? S & {
      use: { [K in keyof T]: () => T[K] };
    }
  : never;

const createSelectors = <S extends UseBoundStore<StoreApi<object>>>(
  _store: S,
) => {
  const store = _store as WithSelectors<typeof _store>;
  store.use = {};
  for (const k of Object.keys(store.getState())) {
    (store.use as any)[k] = () => store((s) => s[k as keyof typeof s]);
  }

  return store;
};

type ApplicationStore = OnboardingWorkflowStore & ProjectStore & WorkflowStore;

const useApplicationStoreBase = createWithEqualityFn<ApplicationStore>()(
  devtools(
    persist(
      (...all) => ({
        ...errorStore(...all),
        ...authStore(...all),
        ...onboardingWorkflowStore(...all),
        ...projectStore(...all),
        ...workflowStore(...all),
      }),
      {
        name: "application-store", // name of the item in the storage (must be unique)
        partialize: (state: ApplicationStore) => ({
          currentIdToken: state.currentIdToken,
          user: state.user,
          isAuthenticated: state.isAuthenticated,
        }),
      },
    ),
    shallow,
  ),
);

// wraps the store with selectors for all state properties
const useApplicationStore = createSelectors(useApplicationStoreBase);
export default useApplicationStore;
