import type { ChangeEvent, FC } from "react";
import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { StepperNavigatorProps } from "../../components/Stepper";
import type { CustomFlowbiteTheme, TabsRef } from "flowbite-react";
import { Card } from "flowbite-react";
import { Button, Tabs, TextInput } from "flowbite-react";
import classNames from "classnames";
import { HiSearch } from "react-icons/hi";
import { MdGridView, MdTableRows } from "react-icons/md";
import { SelectableCard } from "../../components/SelectableCard.tsx";
import { PiStackFill } from "react-icons/pi";
import { SiWebpack } from "react-icons/si";
import { useStepper } from "../../hooks/useStepper.ts";
import { FormProvider, useForm } from "react-hook-form";

interface App {
  id: string;
  name: string;
  description?: string;
  icon?: React.JSXElementConstructor<any>;
  enabled: boolean;
  comingSoon: boolean;
  category?: string;
  paidAlternatives?: string[];
}

const mockApps: App[] = Array.from({ length: 10 }, (_, index) => ({
  id: `app${index + 1}`,
  name: `App ${index + 1}`,
  description: `This is App ${index + 1}`,
  icon: SiWebpack,
  enabled: Math.random() > 0.5,
  comingSoon: Math.random() < 0.5,
}));

export enum AppChooserLayout {
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
  selectedApps: App[];
}

export const ChooseAppsStep: FC<StepperNavigatorProps> = (props) => {
  const [apps, setApps] = useState<App[]>(mockApps);
  const [selectedApps, setSelectedApps] = useState<App[]>([]);

  const methods = useForm<ChooseAppsFormState>({
    defaultValues: {
      selectedApps: [],
    },
  });
  const { isValid } = methods.formState;

  useEffect(() => {
    methods.register("selectedApps", {
      validate: (v) =>
        v?.length ? undefined : "Please select at least one app",
    });
    return () => {
      methods.unregister("selectedApps", {});
    };
  }, []);

  useEffect(() => {
    methods.setValue("selectedApps", selectedApps, {
      shouldTouch: true,
      shouldDirty: true,
      shouldValidate: true,
    });
  }, [selectedApps, isValid]);

  const { goForwards } = useStepper();

  const canProgress = (selectedApps?.length ?? 0) > 0;

  const onProgress = (state: ChooseAppsFormState) => {
    console.log(state);
    if (canProgress) {
      goForwards();
    }
  };

  return (
    <ChooseAppsContext.Provider
      value={{ apps, setApps, selectedApps, setSelectedApps }}
    >
      <FormProvider {...methods}>
        <Card className={"min-h-[50vh] w-full p-4"}>
          <div className={"flex size-full flex-col dark:text-white"}>
            <div className={"flex size-full flex-col overflow-hidden pt-10"}>
              <h3 className={"mx-auto pb-1 text-3xl font-medium"}>
                Pick your Software
              </h3>
              <div className="flex size-full w-full flex-col justify-between overflow-hidden pt-4">
                <AppChooserComposite />
                <div className="mx-auto flex gap-4 py-1">
                  <Button
                    size={"xl"}
                    color={"purple"}
                    onClick={methods.handleSubmit(onProgress)}
                    disabled={!isValid}
                  >
                    <div
                      className={"flex items-center gap-2 whitespace-nowrap"}
                    >
                      <PiStackFill /> Create Stack
                    </div>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </FormProvider>
    </ChooseAppsContext.Provider>
  );
};

const AppChooserComposite: FC = () => {
  const [layout, setLayout] = useState(AppChooserLayout.Grid);
  const { apps, selectedApps, setSelectedApps } = useAppChooser();
  const [filteredApps, setFilteredApps] = useState<App[]>(apps);

  return (
    <div className="flex size-full flex-col gap-8 overflow-hidden">
      <div className="mb-2 flex w-full items-center justify-between gap-2 px-2">
        <div className={"flex w-full justify-center p-1"}>
          <AppSearch apps={apps} onFilter={(fa) => setFilteredApps(fa)} />
          {/*<div className={"w-fit min-w-fit"}>*/}
          {/*  <AppChooserLayoutSelector onChange={setLayout} layout={layout} />*/}
          {/*</div>*/}
        </div>
      </div>
      <div className="mx-auto w-full">
        <AppChooser apps={filteredApps} layout={layout} />
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
        // @eslint-ignore-react/style-prop-object
        style="pills"
        theme={tabTheme}
        ref={tabsRef}
        onActiveTabChange={onSetActiveTab}
      >
        <Tabs.Item icon={MdTableRows} title="" />
        <Tabs.Item icon={MdGridView} title="" />
      </Tabs>
    </div>
  );
};

const AppChooser: FC<{
  apps: App[];
  layout: AppChooserLayout;
}> = ({ apps, layout }) => {
  const { selectedApps, setSelectedApps } = useAppChooser();

  const onClick = (app: App, selected: boolean) => {
    const alreadySelected = selectedApps.some((a) => a.id === app.id);
    if (selected && !alreadySelected) {
      setSelectedApps([...selectedApps, app]);
    } else if (!selected && alreadySelected) {
      setSelectedApps(selectedApps.filter((a) => a.id !== app.id));
    }
  };

  return (
    <div
      className={classNames(
        "flex size-full overflow-y-auto content-start gap-2 justify-center",
        {
          "flex-wrap": layout === AppChooserLayout.Grid,
          "flex-col": layout === AppChooserLayout.List,
        },
      )}
    >
      {apps.map((app) => (
        <AppChooserItem
          key={app.id}
          app={app}
          layout={layout}
          onClick={onClick}
          selected={!!selectedApps.some((a) => a.id === app.id)}
        />
      ))}
    </div>
  );
};

const AppChooserItem: FC<{
  app: App;
  layout: AppChooserLayout;
  onClick?: (app: App, selected: boolean) => void;
  selected?: boolean;
}> = ({ app, onClick, layout, selected }) => {
  const onSelect = () => {
    onClick?.(app, true);
  };
  const onDeselect = () => {
    onClick?.(app, false);
  };

  const Icon = app.icon;

  return (
    <SelectableCard
      className="size-fit p-4"
      onSelect={onSelect}
      onDeselect={onDeselect}
      selected={selected}
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center">
          <div className="flex size-10 items-center justify-center">
            <Icon size={30} />
          </div>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-normal">{app.name}</span>
          <span className="text-xs font-light">{app.description}</span>
        </div>
      </div>
    </SelectableCard>
  );
};

const AppSearch: FC<{
  apps: App[];
  onFilter: (apps: App[]) => void;
}> = ({ apps, onFilter }) => {
  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const filterValue = event.target.value;
    const filter = filterValue
      ? (app: App) => {
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
      placeholder="Search for an application"
      required
      size={32}
      onChange={handleInputChange}
    />
  );
};

type ChooseAppsContextProps = {
  apps: App[];
  setApps: (apps: App[]) => void;
  selectedApps: App[];
  setSelectedApps: (apps: App[]) => void;
};

const ChooseAppsContext = createContext<ChooseAppsContextProps>({
  apps: [],
  setApps: () => {},
  selectedApps: [],
  setSelectedApps: () => {},
});

const useAppChooser = () => {
  const context = useContext(ChooseAppsContext);
  if (!context) {
    throw new Error("useAppChooser must be used within a ChooseAppsStep");
  }
  return context;
};
