import type { FC } from "react";
import { useEffect, useState } from "react";
import React from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { Card } from "flowbite-react";
import useApplicationStore from "../store/ApplicationStore.ts";
import type { Property } from "../../shared/configuration-properties.ts";
import { toFormState } from "../../shared/models/UserStack.ts";
import type { AppTemplate } from "../../shared/models/AppTemplate.ts";
import { ConfigureAppsForm } from "../../components/ConfigureAppsForm.tsx";

export interface ConfigFormSection {
  title: string;
  propertyMap: Map<string, Property[]>;
  defaultOpened?: boolean;
  defaultValues: { [key: string]: any };
}

export const ConfigureAppsStep: FC<
  StepperNavigatorProps & {
    excludedApps?: string[];
  }
> = ({ excludedApps, ...props }) => {
  const { userStack, getStackPacks } = useApplicationStore();

  const [sections, setSections] = useState<ConfigFormSection[]>([]);
  const [stackPacks, setStackPacks] = useState<Map<string, AppTemplate>>(
    new Map(),
  );

  useEffect(() => {
    (async () => {
      const stackPacks = await getStackPacks();
      setStackPacks(stackPacks);

      const sections: ConfigFormSection[] = Object.entries(
        userStack?.stack_packs ?? {},
      )
        .filter(([stackPackId]) => !excludedApps?.includes(stackPackId))
        .map(([stackPackId, appDeployment]) => {
          const config = appDeployment?.configuration;
          const stackPack = stackPacks.get(stackPackId);
          if (!stackPack) {
            return undefined;
          }
          return {
            title: stackPack.name,
            propertyMap: new Map<string, Property[]>([
              [stackPackId, Object.values(stackPack.configuration)],
            ]),
            defaultValues: toFormState(
              config,
              Object.values(stackPack.configuration),
              stackPackId,
            ),
          };
        })
        .filter((section) => section !== undefined) as ConfigFormSection[];
      setSections(sections);
    })();
  }, [getStackPacks, userStack]);

  return (
    <Card className={"min-h-[50vh] w-full p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <div className={"flex size-full flex-col gap-4"}>
          <h3
            className={
              "border-b border-gray-200 pb-1 text-xl font-medium dark:border-gray-700"
            }
          >
            Configure your stack
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
    </Card>
  );
};
