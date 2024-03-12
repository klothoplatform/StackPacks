import type { FC } from "react";
import React from "react";
import type { AppTemplate } from "../shared/models/AppTemplate.ts";
import { FormProvider, useForm } from "react-hook-form";
import { merge } from "ts-deepmerge";
import useApplicationStore from "../pages/store/ApplicationStore.ts";
import { formStateToAppConfig } from "../shared/models/UserStack.ts";
import { UIError } from "../shared/errors.ts";
import { DynamicConfigForm } from "./config/DynamicConfigForm.tsx";
import type { StepperNavigatorProps } from "./Stepper.tsx";
import { StepperNavigator } from "./Stepper.tsx";
import type { Property } from "../shared/configuration-properties.ts";
import type { UpdateStackResponse } from "../api/UpdateStack.ts";

export interface ConfigFormSection {
  title: string;
  propertyMap: Map<string, Property[]>;
  defaultOpened?: boolean;
  defaultValues: { [key: string]: any };
  flat?: boolean;
}

export const ConfigureAppsForm: FC<{
  sections?: ConfigFormSection[];
  stackPacks: Map<string, AppTemplate>;
  stepperProps: StepperNavigatorProps;
  saveButton?: React.JSXElementConstructor<any>;
  onConfig?: (response: UpdateStackResponse) => void;
}> = ({ sections, stackPacks, stepperProps, saveButton, onConfig }) => {
  const methods = useForm({
    defaultValues: merge(...sections.map((s) => s.defaultValues)),
  });

  const SaveButton = saveButton;

  const { isDirty } = methods.formState;

  const { updateStack, addError } = useApplicationStore();

  const onSubmit = methods.handleSubmit(async (data) => {
    if (!isDirty) {
      stepperProps.goForwards();
      return;
    }
    const configuration = formStateToAppConfig(data, stackPacks);
    console.log(configuration);
    let updatedStack: UpdateStackResponse;
    try {
      updatedStack = await updateStack({ configuration });
    } catch (e) {
      addError(
        new UIError({
          errorId: "update-stack-configuration",
          message: "Failed to update stack configuration",
          cause: e,
        }),
      );
    }

    if (onConfig) {
      onConfig(updatedStack);
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
          {SaveButton && <SaveButton onClick={onSubmit} />}
          {!SaveButton && (
            <StepperNavigator {...stepperProps} goForwards={onSubmit} />
          )}
        </div>
      </FormProvider>
    </form>
  );
};
