import type { ChangeEvent, FC } from "react";
import React, { useContext, useEffect, useRef, useState } from "react";
import type { StepperNavigatorProps } from "../../components/Stepper";
import type { CustomFlowbiteTheme, TabsRef } from "flowbite-react";
import { Button, Card, Tabs, TextInput, useThemeMode } from "flowbite-react";
import classNames from "classnames";
import { HiSearch } from "react-icons/hi";
import { MdCheckCircle, MdGridView, MdTableRows } from "react-icons/md";
import { SelectableCard } from "../../components/SelectableCard.tsx";
import { PiStackFill } from "react-icons/pi";
import { FormProvider, useForm } from "react-hook-form";
import useApplicationStore from "../store/ApplicationStore.ts";
import type { AppTemplate } from "../../shared/models/AppTemplate.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { useSearchParams } from "react-router-dom";
import { UIError } from "../../shared/errors.ts";
import { AiOutlineLoading } from "react-icons/ai";
import { setEquals } from "../../shared/object-util.ts";
import { AppLogo } from "../../components/AppLogo.tsx";
import { useScreenSize } from "../../hooks/useScreenSize.ts";
import { AppChooserContext } from "../../context/AppChooserContext.ts";

enum AppChooserLayout {
  List,
  Grid,
}

const tabTheme: CustomFlowbiteTheme["tabs"] = {
  tablist: {
    base: "flex px-1 overflow-visible",
    styles: {
      pills: "flex-wrap font-medium text-sm text-gray-500 dark:text-gray-400",
    },
    tabitem: {
      base: "overflow-visible first:rounded-l-lg last:rounded-r-lg flex items-center justify-center p-1 text-sm font-medium first:ml-0 disabled:cursor-not-allowed disabled:text-gray-400 disabled:dark:text-gray-500 focus:ring-2 focus:ring-primary-300 focus:outline-none border border-gray-200 dark:border-gray-700",
      styles: {
        pills: {
          active: {
            on: "bg-primary-600 text-white",
            off: "bg-white dark:bg-gray-700  hover:text-gray-900 hover:bg-gray-100 dark:hover:bg-gray-600 dark:hover:text-white",
          },
        },
      },
      icon: "h-5 w-5",
    },
  },
  tabpanel: "hidden",
  tabitemcontainer: {
    base: "hidden",
  },
};

export interface ChooseAppsFormState {
  selectedApps: string[];
}

export const ChooseAppsStep: FC<
  StepperNavigatorProps & {
    excludedApps?: string[];
  }
> = ({ excludedApps, ...props }) => {
  const {
    stackPacks,
    updateOnboardingWorkflowState,
    getStackPacks,
    createOrUpdateStack,
    addError,
    userStack,
  } = useApplicationStore();

  const [apps, setApps] = useState<AppTemplate[]>(
    [...stackPacks.values()].filter((app) => !excludedApps?.includes(app.id)),
  );
  const [selectedApps, setSelectedApps] = useState<string[]>(
    userStack
      ? Object.keys(userStack.stack_packs)?.filter(
          (app) => !excludedApps?.includes(app),
        )
      : [],
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  const methods = useForm<ChooseAppsFormState>({
    defaultValues: {
      selectedApps: [],
    },
  });
  const { isValid } = methods.formState;

  useEffect(() => {
    setApps((old) => old.filter((app) => !excludedApps?.includes(app.id)));
  }, [excludedApps]);

  useEffect(() => {
    if (!isLoaded || (isLoaded && !userStack)) {
      return;
    }
    setSelectedApps(
      userStack.stack_packs
        ? Object.keys(userStack.stack_packs).filter(
            (app) => !excludedApps?.includes(app),
          )
        : [],
    );
  }, [userStack, isLoaded, excludedApps]);

  useEffectOnMount(() => {
    // load stack packs
    (async () => {
      const stackPacks = await getStackPacks();
      console.log("ChooseAppsSetp.getStackPacks", stackPacks);
      setApps(
        [...stackPacks.values()].filter(
          (app) => !excludedApps?.includes(app.id),
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
      if (!userStack) {
        await createOrUpdateStack({
          configuration: Object.fromEntries(selectedApps.map((id) => [id, {}])),
        });
      } else {
        if (
          setEquals(
            new Set(selectedApps),
            new Set(Object.keys(userStack.stack_packs)),
          )
        ) {
          setIsSubmitting(false);
          props.goForwards();
          return;
        }
        await createOrUpdateStack({
          configuration: Object.fromEntries(
            selectedApps.map((id) => [
              id,
              userStack.stack_packs[id]?.configuration ?? {},
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
        <Card className={"min-h-[50vh] w-full overflow-hidden p-4"}>
          <div className={"flex size-full flex-col dark:text-white"}>
            <div className={"flex size-full flex-col overflow-hidden pt-10"}>
              <h3 className={"mx-auto pb-1 text-3xl font-medium"}>
                Pick your Software
              </h3>
              <div className="flex size-full w-full flex-col justify-between overflow-hidden pt-4">
                <div className={"size-full overflow-auto p-4"}>
                  <AppChooserComposite />
                </div>
                <div className="mx-auto flex gap-4 py-1">
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
                      {!isSubmitting && <PiStackFill />}{" "}
                      {userStack ? "Update" : "Create"} Stack
                    </div>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </FormProvider>
    </AppChooserContext.Provider>
  );
};

export const AppChooserComposite: FC = () => {
  const { apps } = useAppChooser();
  const [filteredApps, setFilteredApps] = useState<AppTemplate[]>([...apps]);
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

const AppChooserLayoutSelector: FC<{
  layout?: AppChooserLayout;
  onChange: (layout: AppChooserLayout) => void;
}> = ({ layout, onChange }) => {
  const tabsRef = useRef<TabsRef>(null);

  const onSetActiveTab = (layout: AppChooserLayout) => {
    onChange(layout);
  };

  useEffect(() => {
    if (tabsRef.current) {
      tabsRef.current.setActiveTab(layout);
    }
  }, [layout]);

  return (
    <div className="w-fit p-2">
      <Tabs
        // eslint-disable-next-line react/style-prop-object
        style="pills"
        theme={tabTheme}
        ref={tabsRef}
        onActiveTabChange={onSetActiveTab}
      >
        <Tabs.Item
          icon={MdTableRows}
          title=""
          active={layout === AppChooserLayout.List}
        />
        <Tabs.Item
          icon={MdGridView}
          title=""
          active={layout === AppChooserLayout.Grid}
        />
      </Tabs>
    </div>
  );
};

const AppChooser: FC<{
  apps: AppTemplate[];
  layout: AppChooserLayout;
}> = ({ apps, layout }) => {
  const { selectedApps, setSelectedApps } = useAppChooser();
  const [_, setSearchParams] = useSearchParams();
  const onClick = (app: AppTemplate, selected: boolean) => {
    const alreadySelected = selectedApps.some((a) => a === app.id);
    let updatedSelection = [...selectedApps];
    if (selected && !alreadySelected) {
      updatedSelection.push(app.id);
    } else if (!selected && alreadySelected) {
      updatedSelection = updatedSelection.filter((a) => a !== app.id);
    }
    setSearchParams((prev) => ({
      ...Object.fromEntries(prev.entries()),
      selectedApps: updatedSelection.join(","),
    }));
    setSelectedApps(updatedSelection);
  };

  return (
    <div
      className={classNames("flex w-full max-h-full h-fit", {
        "flex-wrap": layout === AppChooserLayout.Grid,
        "flex-col items-center": layout === AppChooserLayout.List,
      })}
    >
      {apps.map((app, index) => (
        <div
          key={index}
          className={classNames("my-0.5", {
            "w-1/3": layout === AppChooserLayout.Grid,
            "w-full max-w-[50rem]": layout === AppChooserLayout.List,
          })}
        >
          <div className={"p-1"}>
            <AppChooserItem
              app={app}
              onClick={onClick}
              selected={!!selectedApps.some((a) => a === app.id)}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

const AppChooserItem: FC<{
  app: AppTemplate;
  onClick?: (app: AppTemplate, selected: boolean) => void;
  selected?: boolean;
}> = ({ app, onClick, selected }) => {
  const { mode } = useThemeMode();

  const onSelect = () => {
    onClick?.(app, true);
  };
  const onDeselect = () => {
    onClick?.(app, false);
  };

  return (
    <SelectableCard
      onSelect={onSelect}
      onDeselect={onDeselect}
      outline
      selected={selected}
    >
      <div className="h-fit w-full px-2 pt-2">
        <div className="flex size-full flex-col gap-4">
          <div className="flex w-full items-center gap-4">
            <div className="flex items-center">
              <div className="flex size-10 items-center justify-center">
                <AppLogo mode={mode} appId={app.id} />
              </div>
            </div>
            <div className="flex w-full flex-col overflow-hidden">
              <div className="flex justify-between">
                <span
                  title={app.name}
                  className="lg:text-md w-fit overflow-hidden text-ellipsis text-sm font-normal"
                >
                  {app.name}
                </span>
                {selected && (
                  <MdCheckCircle
                    className={"text-primary-700 dark:text-primary-400"}
                  />
                )}
              </div>
              <span
                title={app.description}
                className="line-clamp-2 h-8 overflow-hidden text-ellipsis text-xs font-light leading-tight text-gray-600 dark:text-gray-400"
              >
                {app.description}
              </span>
            </div>
          </div>
        </div>
        <div className="flex justify-end py-2">
          <Button
            size="xs"
            color={mode}
            className="w-fit"
            onClick={(e) => {
              window.open(`https://klo.dev/stacksnap/apps/${app.id}`, "_blank");
              e.stopPropagation();
            }}
          >
            Details
          </Button>
        </div>
      </div>
    </SelectableCard>
  );
};

const AppSearch: FC<{
  apps: AppTemplate[];
  onFilter: (apps: AppTemplate[]) => void;
}> = ({ apps, onFilter }) => {
  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const filterValue = event.target.value;
    const filter = filterValue
      ? (app: AppTemplate) => {
          return filterValue
            ? app.name
                .toLowerCase()
                .replace(/[\s-_]/g, "")
                .includes(filterValue.toLowerCase().replaceAll(/[-_ ]/g, ""))
            : true;
        }
      : undefined;

    const filteredApps = filter ? apps.filter(filter) : apps;
    onFilter(filteredApps);
  };

  return (
    <TextInput
      icon={HiSearch}
      type="search"
      placeholder="Search for an application by name"
      required
      size={32}
      onChange={handleInputChange}
    />
  );
};

const useAppChooser = () => {
  const context = useContext(AppChooserContext);
  if (!context) {
    throw new Error("useAppChooser must be used within a ChooseAppsStep");
  }
  return context;
};
