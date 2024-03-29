import type { FC } from "react";
import { useState } from "react";
import React from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import useApplicationStore from "../store/ApplicationStore.ts";
import type { Property } from "../../shared/configuration-properties.ts";
import {
  formStateToAppConfig,
  toFormState,
} from "../../shared/models/Project.ts";
import { FormProvider, useForm } from "react-hook-form";
import { UIError } from "../../shared/errors.ts";
import { DynamicConfigForm } from "../../components/config/DynamicConfigForm.tsx";
import { Button } from "flowbite-react";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import { useNavigate } from "react-router-dom";

export const ConfigureAppStep: FC<
  StepperNavigatorProps & {
    appId: string;
  }
> = ({ appId, ...props }) => {
  return (
    <div className={"flex size-full flex-col overflow-visible dark:text-white"}>
      <ConfigureAppForm stepperProps={props} appId={appId} />
    </div>
  );
};

export const ConfigureAppForm: FC<{
  appId: string;
  stepperProps: StepperNavigatorProps;
}> = ({ appId }) => {
  const { project, stackPacks } = useApplicationStore();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const appDeployment = project?.stack_packs?.[appId];
  const config = appDeployment?.configuration;
  const stackPack = stackPacks.get(appId);
  const propertyMap = new Map<string, Property[]>([
    [appId, Object.values(stackPack.configuration)],
  ]);
  const defaultValues = toFormState(
    config,
    Object.values(stackPack.configuration),
    appId,
  );

  const methods = useForm({
    defaultValues,
  });

  const { isDirty } = methods.formState;

  const { updateProject, addError, installApp } = useApplicationStore();

  const onSubmit = methods.handleSubmit(async (data) => {
    setIsSubmitting(true);

    try {
      const configuration = formStateToAppConfig(data, stackPacks);
      try {
        await updateProject({ configuration });
      } catch (e) {
        addError(
          new UIError({
            errorId: "update-stack-configuration",
            message: "Failed to update stack configuration",
            cause: e,
          }),
        );
        return;
      }

      try {
        const response = await installApp(appId);
        navigate(
          `/project/apps/${response.app_id}/workflows/${response.workflow_type.toLowerCase()}/runs/${response.run_number}`,
        );
      } catch (e) {
        addError(
          new UIError({
            errorId: "deploy-updated-app-configuration",
            message:
              "Failed to trigger deployment of updated app configuration",
            cause: e,
          }),
        );
      }
      navigate("/project");
    } finally {
      setIsSubmitting(false);
    }
  });

  return (
    <form className={"flex h-fit min-h-0 flex-col gap-2"} onSubmit={onSubmit}>
      <FormProvider {...methods}>
        <div className={"h-fit min-h-0 w-full overflow-y-auto"}>
          <DynamicConfigForm
            sections={[
              {
                title: stackPack.name,
                propertyMap,
                flat: true,
              },
            ]}
          />
        </div>
        <div className="ml-auto flex gap-4 justify-self-end">
          <Button
            color={"purple"}
            onClick={onSubmit}
            isProcessing={isSubmitting}
            processingSpinner={
              <AiOutlineLoading3Quarters className="animate-spin" />
            }
            disabled={isSubmitting || !isDirty}
          >
            Save and Deploy
          </Button>
        </div>
      </FormProvider>
    </form>
  );
};
