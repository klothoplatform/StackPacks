import type { FC } from "react";
import React, { useState } from "react";
import { UIError } from "../../shared/errors.ts";
import { ErrorBoundary } from "react-error-boundary";
import { FallbackRenderer } from "../../components/FallbackRenderer.tsx";
import { trackError } from "../store/ErrorStore.ts";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Dropdown,
  Label,
  TextInput,
  useThemeMode,
} from "flowbite-react";
import { MdChevronLeft } from "react-icons/md";
import useApplicationStore from "../store/ApplicationStore.ts";
import type { Project } from "../../shared/models/Project.ts";
import { isProjectDeployed } from "../../shared/models/Project.ts";
import { FormProvider, useForm } from "react-hook-form";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import { awsDefaultRegions, awsRegions } from "../../shared/aws-regions.ts";

export const ConfigureEnvironmentPage: FC = () => {
  const { project } = useApplicationStore();

  const navigate = useNavigate();
  const { mode } = useThemeMode();

  return (
    <ErrorBoundary
      fallbackRender={FallbackRenderer}
      onError={(error, info) => {
        trackError(
          new UIError({
            message: "Uncaught error in ConfigureAppWorkflow",
            errorId: "ConfigureAppWorkflow:ErrorBoundary",
            cause: error,
            data: {
              info,
            },
          }),
        );
      }}
    >
      <div className="flex max-w-xl flex-col justify-center gap-4 p-4">
        <div className="flex gap-4 px-1">
          <Button
            color={mode}
            outline
            size="xs"
            className="flex items-center gap-2 whitespace-nowrap"
            onClick={() => navigate("/project")}
          >
            <MdChevronLeft /> Back
          </Button>
          <h2 className="text-2xl font-medium">Configure Environment</h2>
        </div>
        <ConfigureEnvironmentForm project={project} />
      </div>
    </ErrorBoundary>
  );
};

interface ConfigureEnvironmentFormState {
  region: string;
  assumedRoleArn: string;
}

export const ConfigureEnvironmentForm: FC<{
  project: Project;
}> = ({ project }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const methods = useForm<ConfigureEnvironmentFormState>({
    defaultValues: {
      region: project.region,
      assumedRoleArn: project.assumed_role_arn || "",
    },
  });

  const { isDirty } = methods.formState;

  const { updateProject, addError } = useApplicationStore();

  const onSubmit = methods.handleSubmit(async (data) => {
    setIsSubmitting(true);

    try {
      try {
        await updateProject({
          region: isProjectDeployed(project) ? undefined : data.region,
          assumed_role_arn: data.assumedRoleArn,
        });
      } catch (e) {
        addError(
          new UIError({
            errorId: "update-project-configuration",
            message: "Failed to update project configuration",
            cause: e,
          }),
        );
        return;
      }

      navigate("/project");
    } finally {
      setIsSubmitting(false);
    }
  });

  const watchRegion = methods.watch("region");

  return (
    <form onSubmit={onSubmit} className={"flex h-fit min-h-0 flex-col gap-8"}>
      <div className={"flex h-fit min-h-0 flex-col gap-6"}>
        <FormProvider {...methods}>
          <div className={"flex flex-col gap-2"}>
            <Label>Deployment Role ARN</Label>
            <TextInput
              name="assumedRoleArn"
              placeholder="Deployment Role ARN"
              sizing={"sm"}
              {...methods.register("assumedRoleArn")}
            />
          </div>
          <div className={"flex flex-col gap-2"}>
            <Label>Region</Label>
            <Dropdown
              color={"purple"}
              label={awsRegions[watchRegion] || "Select a region"}
              disabled={isProjectDeployed(project)}
              placement={"bottom-start"}
              size={"sm"}
              theme={{
                floating: {
                  base: "z-10 w-fit rounded divide-y divide-gray-100 shadow focus:outline-none max-h-48 overflow-y-auto",
                },
              }}
            >
              {Object.entries(awsDefaultRegions).map(([region, name]) => {
                return (
                  <Dropdown.Item
                    key={region}
                    value={region}
                    onClick={() => methods.setValue("region", region)}
                  >
                    {name}
                  </Dropdown.Item>
                );
              })}
            </Dropdown>
          </div>
        </FormProvider>
      </div>

      <Button
        className={"w-fit"}
        color={"purple"}
        onClick={onSubmit}
        isProcessing={isSubmitting}
        processingSpinner={
          <AiOutlineLoading3Quarters className="animate-spin" />
        }
        disabled={isSubmitting || !isDirty}
      >
        Save
      </Button>
    </form>
  );
};
