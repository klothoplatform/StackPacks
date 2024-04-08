import type { FC } from "react";
import React, { useEffect, useState } from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import useApplicationStore from "../store/ApplicationStore.ts";
import type { Property } from "../../shared/configuration-properties.ts";
import { toFormState } from "../../shared/models/Project.ts";
import type { Stackpack } from "../../shared/models/Stackpack.ts";
import { ConfigureAppsForm } from "../../components/ConfigureAppsForm.tsx";
import { AppLogo } from "../../components/AppLogo.tsx";
import { useThemeMode } from "flowbite-react";

export interface ConfigFormSection {
  icon?: React.ReactNode;
  title: string;
  propertyMap: Map<string, Property[]>;
  defaultOpened?: boolean;
  defaultValues: { [key: string]: any };
}

export interface ConfigureAppStepProps extends StepperNavigatorProps {
  selectedApp: string;
}

export const ConfigureAppStep: FC<ConfigureAppStepProps> = ({
  selectedApp,
  ...props
}) => {
  const { project, getStackPacks } = useApplicationStore();
  const { mode } = useThemeMode();
  const [sections, setSections] = useState<ConfigFormSection[]>([]);
  const [stackPacks, setStackPacks] = useState<Map<string, Stackpack>>(
    new Map(),
  );
  const [selectedAppName, setSelectedAppName] = useState<string>(selectedApp);

  useEffect(() => {
    (async () => {
      const stackPacks = await getStackPacks();
      setStackPacks(stackPacks);
      setSelectedAppName(stackPacks.get(selectedApp)?.name ?? selectedApp);
      const appDeployment = project?.stack_packs?.[selectedApp];
      const config = appDeployment?.configuration;
      const stackPack = stackPacks.get(appDeployment.app_id);
      const sections = [];
      if (stackPack) {
        sections.push({
          icon: (
            <AppLogo
              appId={appDeployment.app_id}
              className={"h-4"}
              mode={mode}
            />
          ),
          title: stackPack.name,
          propertyMap: new Map<string, Property[]>([
            [appDeployment.app_id, Object.values(stackPack.configuration)],
          ]),
          defaultValues: toFormState(
            config,
            Object.values(stackPack.configuration),
            appDeployment.app_id,
          ),
          collapseOptionalFields: true,
        });
      }
      setSections(sections);
    })();
  }, [getStackPacks, mode, project, selectedApp]);

  return (
    <div className={"min-h-[50vh] w-full p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <div className={"flex size-full flex-col gap-4"}>
          {selectedAppName && (
            <h3 className={"pb-1 text-xl font-medium dark:border-gray-700"}>
              Configure {selectedAppName}
            </h3>
          )}
          {sections.length > 0 && (
            <ConfigureAppsForm
              sections={sections}
              stepperProps={props}
              stackPacks={stackPacks}
            />
          )}
        </div>
      </div>
    </div>
  );
};
