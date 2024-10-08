import type { Stackpack } from "../shared/models/Stackpack.ts";
import type { ChangeEvent, FC } from "react";
import React, { useEffect, useRef, useState } from "react";
import {
  Button,
  type CustomFlowbiteTheme,
  Tabs,
  type TabsRef,
  TextInput,
  useThemeMode,
} from "flowbite-react";
import { HiSearch } from "react-icons/hi";
import { useSearchParams } from "react-router-dom";
import classNames from "classnames";
import { useScreenSize } from "../hooks/useScreenSize.ts";
import { MdCheckCircle, MdGridView, MdTableRows } from "react-icons/md";
import { SelectableCard } from "./SelectableCard.tsx";
import { AppLogo } from "./AppLogo.tsx";
import { AppChooserLayout } from "./AppChooser.ts";
import { useAppChooser } from "../hooks/UseAppChooser.tsx";

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

export const AppChooserComposite: FC = () => {
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

export const AppChooserLayoutSelector: FC<{
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

export const AppChooser: FC<{
  apps: Stackpack[];
  layout: AppChooserLayout;
  mode?: "multi" | "single";
}> = ({ apps, layout, mode }) => {
  mode = mode ?? "multi";
  const { selectedApps, setSelectedApps } = useAppChooser();
  const [_, setSearchParams] = useSearchParams();
  const onClick = (app: Stackpack, selected: boolean) => {
    if (mode === "single") {
      setSelectedApps(selectedApps.some((a) => a === app.id) ? [] : [app.id]);
      setSearchParams((prev) => ({
        ...Object.fromEntries(prev.entries()),
        selectedApps: app.id,
      }));
      return;
    }

    // multi
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

export const AppChooserItem: FC<{
  app: Stackpack;
  onClick?: (app: Stackpack, selected: boolean) => void;
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
      className={classNames({
        "bg-primary-200/50 dark:bg-primary-900/50": selected,
      })}
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

export const AppSearch: FC<{
  apps: Stackpack[];
  onFilter: (apps: Stackpack[]) => void;
}> = ({ apps, onFilter }) => {
  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const filterValue = event.target.value;
    const filter = filterValue
      ? (app: Stackpack) => {
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
