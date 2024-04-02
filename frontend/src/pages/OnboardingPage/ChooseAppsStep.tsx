import type { FC } from "react";
import React, { useEffect, useState } from "react";
import type { StepperNavigatorProps } from "../../components/Stepper";
import { Button } from "flowbite-react";
import { FormProvider, useForm } from "react-hook-form";
import useApplicationStore from "../store/ApplicationStore.ts";
import type { Stackpack } from "../../shared/models/Stackpack.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { UIError } from "../../shared/errors.ts";
import { AiOutlineLoading } from "react-icons/ai";
import { setEquals } from "../../shared/object-util.ts";
import {
  AppChooserContext,
  useAppChooser,
} from "../../context/AppChooserContext.tsx";
import { useScreenSize } from "../../hooks/useScreenSize.ts";
import { AppChooserLayout } from "../../components/AppChooser.ts";
import {
  AppChooser,
  AppChooserLayoutSelector,
  AppSearch,
} from "../../components/AppChooser.tsx";

export interface ChooseAppsFormState {
  selectedApps: string[];
}

export const ChooseAppsStep: FC<StepperNavigatorProps & {}> = ({
  ...props
}) => {
  const {
    stackPacks,
    updateOnboardingWorkflowState,
    getStackPacks,
    createOrUpdateProject,
    addError,
    project,
  } = useApplicationStore();

  const [apps, setApps] = useState<Stackpack[]>([...stackPacks.values()]);
  const [selectedApps, setSelectedApps] = useState<string[]>(
    Object.keys(project?.stack_packs ?? {}) ?? [],
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  const methods = useForm<ChooseAppsFormState>({
    defaultValues: {
      selectedApps: [],
    },
  });
  const { isValid } = methods.formState;

  useEffectOnMount(() => {
    // exclude apps that are already in the project since there's no bulk delete option right now
    const currentProjectApps = Object.keys(project?.stack_packs ?? {});

    // load stack packs
    (async () => {
      const stackPacks = await getStackPacks();
      setApps(
        [...stackPacks.values()].filter(
          (sp) => !currentProjectApps.includes(sp.id),
        ),
      );
    })();

    // register form fields
    methods.register("selectedApps", {
      validate: (v) =>
        v?.length ? undefined : "Please select at least one app",
    });

    setIsLoaded(true);

    return () => {
      methods.unregister("selectedApps", {});
    };
  });

  useEffect(() => {
    const currentProjectApps = Object.keys(project?.stack_packs ?? {});
    setApps(
      [...stackPacks.values()].filter(
        (sp) => !currentProjectApps.includes(sp.id),
      ),
    );
  }, [project, stackPacks]);

  useEffect(() => {
    methods.setValue("selectedApps", selectedApps, {
      shouldTouch: true,
      shouldDirty: true,
      shouldValidate: true,
    });
  }, [selectedApps, isValid, methods]);

  const canProgress = isLoaded && (selectedApps?.length ?? 0) > 0;

  const completeStep = async (state: ChooseAppsFormState) => {
    console.log("completeStep", { state });
    if (!canProgress) {
      return;
    }
    setIsSubmitting(true);
    updateOnboardingWorkflowState({
      selectedStackPacks: state.selectedApps,
    });

    try {
      if (!project) {
        await createOrUpdateProject({
          configuration: Object.fromEntries(selectedApps.map((id) => [id, {}])),
        });
      } else {
        if (
          setEquals(
            new Set(selectedApps),
            new Set(Object.keys(project.stack_packs)),
          )
        ) {
          setIsSubmitting(false);
          props.goForwards();
          return;
        }
        await createOrUpdateProject({
          configuration: Object.fromEntries(
            selectedApps.map((id) => [
              id,
              project.stack_packs[id]?.configuration ?? {},
            ]),
          ),
        });
      }
    } catch (e) {
      addError(
        new UIError({
          message: "Stack creation failed.",
          cause: e,
        }),
      );
      return;
    } finally {
      setIsSubmitting(false);
    }

    props.goForwards();
  };

  return (
    <AppChooserContext.Provider
      value={{ apps, setApps, selectedApps, setSelectedApps }}
    >
      <FormProvider {...methods}>
        <div className={"min-h-[50vh] w-full overflow-hidden p-4"}>
          <div className={"flex size-full flex-col dark:text-white"}>
            <div className={"flex size-full flex-col overflow-hidden pt-10"}>
              <h2 className={"mx-auto pb-1 text-3xl font-medium"}>
                Pick your software
              </h2>
              <div className="flex size-full w-full flex-col justify-between overflow-hidden pt-4">
                <div className={"size-full overflow-auto p-4"}>
                  <AppChooserComposite />
                </div>

                <div className="mx-auto flex gap-4 py-1">
                  {selectedApps.length > 0 && (
                    <Button
                      className={"size-fit"}
                      size={"xl"}
                      color={"purple"}
                      onClick={methods.handleSubmit(completeStep)}
                      isProcessing={isSubmitting}
                      processingSpinner={
                        <AiOutlineLoading className={"animate-spin"} />
                      }
                      disabled={isSubmitting || !isValid}
                    >
                      <div
                        className={"flex items-center gap-2 whitespace-nowrap"}
                      >
                        {project?.id ? "Update" : "Create"} Project
                      </div>
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </FormProvider>
    </AppChooserContext.Provider>
  );
};

const AppChooserComposite: FC = () => {
  const { apps } = useAppChooser();
  const [filteredApps, setFilteredApps] = useState<Stackpack[]>([...apps]);
  const { isXSmallScreen } = useScreenSize();
  const [selectedLayout, setSelectedLayout] = useState<AppChooserLayout>(
    AppChooserLayout.Grid,
  );

  useEffect(() => {
    setFilteredApps(apps);
  }, [apps]);

  return (
    <div className="flex size-full flex-col gap-2 overflow-hidden">
      <div className="mb-2 flex w-full items-center justify-between gap-2 px-2">
        <div className={"flex w-full justify-center p-1"}>
          <AppSearch apps={apps} onFilter={(fa) => setFilteredApps(fa)} />
        </div>
      </div>
      <div className="mx-auto h-fit max-h-full w-full overflow-y-auto">
        <div className={"ml-auto w-fit min-w-fit"}>
          <AppChooserLayoutSelector
            onChange={(layout) => setSelectedLayout(layout)}
            layout={selectedLayout}
          />
        </div>
        <AppChooser
          apps={filteredApps}
          layout={
            isXSmallScreen || filteredApps.length < 3
              ? AppChooserLayout.List
              : selectedLayout
          }
        />
      </div>
    </div>
  );
};
