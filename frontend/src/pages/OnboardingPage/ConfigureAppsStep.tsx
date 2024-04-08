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

export const ConfigureAppsStep: FC<StepperNavigatorProps> = ({ ...props }) => {
  const { project, getStackPacks } = useApplicationStore();
  const { mode } = useThemeMode();
  const [sections, setSections] = useState<ConfigFormSection[]>([]);
  const [stackPacks, setStackPacks] = useState<Map<string, Stackpack>>(
    new Map(),
  );

  useEffect(() => {
    (async () => {
      const stackPacks = await getStackPacks();
      setStackPacks(stackPacks);

      const sections: ConfigFormSection[] = Object.entries(
        project?.stack_packs ?? {},
      )
        .map(([stackPackId, appDeployment]) => {
          const config = appDeployment?.configuration;
          const stackPack = stackPacks.get(stackPackId);
          if (!stackPack) {
            return undefined;
          }
          return {
            icon: <AppLogo appId={stackPackId} className={"h-4"} mode={mode} />,
            title: stackPack.name,
            propertyMap: new Map<string, Property[]>([
              [stackPackId, Object.values(stackPack.configuration)],
            ]),
            defaultValues: toFormState(
              config,
              Object.values(stackPack.configuration),
              stackPackId,
            ),
            collapseOptionalFields: true,
          };
        })
        .filter((section) => section !== undefined) as ConfigFormSection[];
      setSections(sections);
    })();
  }, [getStackPacks, mode, project]);

  return (
    <div className={"min-h-[50vh] w-full p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <div className={"flex size-full flex-col gap-4"}>
          <h3 className={"pb-1 text-xl font-medium dark:border-gray-700"}>
            Configure selected applications
          </h3>
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
