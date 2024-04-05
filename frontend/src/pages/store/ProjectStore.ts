import type { StateCreator } from "zustand";
import type { ErrorStore } from "./ErrorStore";
import type {
  Project,
  ProjectModification,
} from "../../shared/models/Project.ts";
import type { Stackpack } from "../../shared/models/Stackpack.ts";
import { resolveDefaultConfiguration } from "../../shared/models/Stackpack.ts";
import type { AuthStore } from "./AuthStore.ts";
import { getStackPacks } from "../../api/GetStackPacks.ts";
import type { UpdateProjectResponse } from "../../api/UpdateProject.ts";
import { updateProject } from "../../api/UpdateProject.ts";
import type { CreateStackResponse } from "../../api/CreateProject.ts";
import { createProject } from "../../api/CreateProject.ts";
import { merge } from "ts-deepmerge";
import type { UpdateAppResponse } from "../../api/UpdateApp.ts";
import { updateApp } from "../../api/UpdateApp.ts";
import { removeApp } from "../../api/RemoveApp.ts";
import { getProject } from "../../api/GetProject.ts";

export interface ProjectStoreState {
  project?: Project;
  stackPacks: Map<string, Stackpack>;
}

export interface ProjectStoreBase extends ProjectStoreState {
  createProject: (stack: ProjectModification) => Promise<CreateStackResponse>;
  createOrUpdateProject: (
    stack: ProjectModification,
  ) => Promise<CreateStackResponse | UpdateProjectResponse>;
  getProject: (refresh?: boolean) => Promise<Project>;
  getStackPacks: (forceRefresh?: boolean) => Promise<Map<string, Stackpack>>;
  removeApp: (appId: string) => Promise<void>;
  resetProjectState: () => void;
  updateApp: (
    appId: string,
    configuration: Record<string, any>,
  ) => Promise<UpdateAppResponse>;
  updateProject: (stack: ProjectModification) => Promise<UpdateProjectResponse>;
}

const initialState: () => ProjectStoreState = () => ({
  stackPacks: new Map(),
});

export type ProjectStore = ProjectStoreBase & ErrorStore & AuthStore;

export const projectStore: StateCreator<
  ProjectStore,
  [],
  [],
  ProjectStoreBase
> = (set: (state: object, replace?: boolean, id?: string) => any, get) => ({
  ...initialState(),
  resetProjectState: () => set(initialState(), false, "resetProjectState"),
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
        project: response.stack,
      },
      false,
      "createProject",
    );
    return response;
  },
  createOrUpdateProject: async (modifications: ProjectModification) => {
    const appTemplates = await get().getStackPacks();
    const defaultConfiguration = Object.fromEntries(
      Object.keys(modifications.configuration ?? {}).map((appId) => [
        appId,
        resolveDefaultConfiguration(appTemplates.get(appId)),
      ]),
    );

    // handle the case where the user has a project and is updating it
    const project = await get().getProject();
    if (project) {
      modifications = {
        ...modifications,
        configuration: { ...modifications.configuration },
      };
      Object.entries(modifications.configuration).forEach(([key, value]) => {
        if (value === undefined || Object.keys(value).length === 0) {
          modifications.configuration[key] =
            project.stack_packs[key]?.configuration ??
            defaultConfiguration[key] ??
            modifications.configuration[key];
        }
      });
      return await get().updateProject(modifications);
    }

    // handle the case where the user does not have a stack and is creating one
    modifications = { ...modifications };
    modifications.configuration = merge(
      defaultConfiguration,
      modifications.configuration,
    );
    if (!modifications.region)
      // set a default region if none is provided on creation
      modifications.region = "us-east-1";
    return await get().createProject(modifications);
  },
  updateProject: async (stack: Partial<Project>) => {
    const idToken = await get().getIdToken();
    const response = await updateProject({ stack, idToken });
    set(
      {
        project: response.stack,
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
  updateApp: async (appId: string, configuration: Record<string, any>) => {
    const idToken = await get().getIdToken();
    const response = await updateApp({ appId, configuration, idToken });
    set(
      {
        project: response.stack,
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
        project: response.stack,
      },
      false,
      "removeApp",
    );
  },
});
