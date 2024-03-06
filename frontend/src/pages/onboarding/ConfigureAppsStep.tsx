import type { FC } from "react";
import { useEffect, useState } from "react";
import React from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Card } from "flowbite-react";
import useApplicationStore from "../store/ApplicationStore.ts";
import { DynamicConfigForm } from "../../components/config/DynamicConfigForm.tsx";
import type { Property } from "../../shared/configuration-properties.ts";
import {
  resolveConfigFromFormState,
  toFormState,
} from "../../shared/models/UserStack.ts";
import { FormProvider, useForm } from "react-hook-form";
import { merge } from "ts-deepmerge";
import type { AppTemplate } from "../../shared/models/AppTemplate.ts";
import { resolveAppTemplates } from "../../shared/models/AppTemplate.ts";
import { UIError } from "../../shared/errors.ts";

export interface ConfigFormSection {
  title: string;
  propertyMap: Map<string, Property[]>;
  defaultOpened?: boolean;
  defaultValues: { [key: string]: any };
}

export const ConfigureAppsStep: FC<StepperNavigatorProps> = ({ ...props }) => {
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
            <ConfigForm
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

const ConfigForm: FC<{
  sections?: ConfigFormSection[];
  stackPacks: Map<string, AppTemplate>;
  stepperProps: StepperNavigatorProps;
}> = ({ sections, stackPacks, stepperProps }) => {
  const methods = useForm({
    defaultValues: merge(...sections.map((s) => s.defaultValues)),
  });

  const { isDirty } = methods.formState;

  const { updateStack, addError } = useApplicationStore();

  const onSubmit = methods.handleSubmit(async (data) => {
    if (!isDirty) {
      stepperProps.goForwards();
      return;
    }

    const packs = [
      ...new Set(
        resolveAppTemplates(
          Object.keys(data)
            .map((f) => (f.includes("#") ? f.split("#")[0] : undefined))
            .filter((f) => f !== undefined),
          stackPacks,
        ),
      ),
    ];
    const configuration = Object.fromEntries(
      packs.map((pack) => [
        pack.id,
        resolveConfigFromFormState(
          Object.fromEntries(
            Object.entries(data)
              .filter(([key]) => key.startsWith(pack.id + "#"))
              .map(([key, value]) => [
                key.includes("#") ? key.split("#")[1] : key,
                value,
              ]),
          ),
          Object.values(pack.configuration),
        ),
      ]),
    );
    console.log(configuration);
    try {
      await updateStack({ configuration });
    } catch (e) {
      addError(
        new UIError({
          errorId: "update-stack-configuration",
          message: "Failed to update stack configuration",
          cause: e,
        }),
      );
    }
    stepperProps.goForwards();
  });

  return (
    <form className={"flex h-fit min-h-0 flex-col gap-2"} onSubmit={onSubmit}>
      <FormProvider {...methods}>
        <div className={"h-fit min-h-0 w-full overflow-y-auto"}>
          <DynamicConfigForm sections={sections} />
        </div>
        <div className="ml-auto flex gap-4 justify-self-end">
          <StepperNavigator {...stepperProps} goForwards={onSubmit} />
        </div>
      </FormProvider>
    </form>
  );
};
