import type { FC } from "react";
import React, { useEffect, useState } from "react";
import { UIError } from "../shared/errors.ts";
import { ErrorBoundary } from "react-error-boundary";
import { FallbackRenderer } from "../components/FallbackRenderer.tsx";
import { trackError } from "./store/ErrorStore.ts";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Dropdown,
  Label,
  TextInput,
  useThemeMode,
} from "flowbite-react";
import { MdChevronLeft } from "react-icons/md";
import useApplicationStore from "./store/ApplicationStore.ts";
import type { Project } from "../shared/models/Project.ts";
import { isProjectDeployed } from "../shared/models/Project.ts";
import { FormProvider, useForm } from "react-hook-form";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import { awsDefaultRegions, awsRegions } from "../shared/aws-regions.ts";
import { CollapsibleSection } from "../components/CollapsibleSection.tsx";
import { CreateRoleStep } from "../components/CreateRoleStep.tsx";
import { Container } from "../components/Container.tsx";
import { InstructionalStep } from "../components/InstructionalStep.tsx";
import { PolicyViewer } from "../components/PolicyViewer.tsx";

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
      <div className="flex max-h-full w-full flex-col gap-4 overflow-y-auto py-4 pl-4 [&>*]:max-w-xl">
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
        <div className="max-h-full">
          <ConfigureEnvironmentForm project={project} />
        </div>
      </div>
    </ErrorBoundary>
  );
};

interface ConfigureEnvironmentFormState {
  region: string;
  assumedRoleArn: string;
  assumedRoleExternalId: string;
}

export const ConfigureEnvironmentForm: FC<{
  project: Project;
}> = ({ project }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const { updateProject, addError } = useApplicationStore();
  const [externalId, setExternalId] = useState<string>(
    project.assumed_role_external_id || crypto.randomUUID(),
  );
  const { mode } = useThemeMode();

  useEffect(() => {
    setExternalId(project.assumed_role_external_id || crypto.randomUUID());
  }, [project.assumed_role_external_id]);

  const methods = useForm<ConfigureEnvironmentFormState>({
    defaultValues: {
      region: project.region,
      assumedRoleArn: project.assumed_role_arn || "",
      assumedRoleExternalId: externalId,
    },
  });

  const { isDirty, errors } = methods.formState;

  const onSubmit = methods.handleSubmit(async (data) => {
    setIsSubmitting(true);

    try {
      try {
        await updateProject({
          region: isProjectDeployed(project) ? undefined : data.region,
          assumed_role_arn: data.assumedRoleArn,
          assumed_role_external_id: data.assumedRoleExternalId,
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
              helperText={
                <span className={"text-xs text-red-600 dark:text-red-400"}>
                  {errors.assumedRoleArn?.message}
                </span>
              }
              name="assumedRoleArn"
              placeholder="arn:aws:iam::<account-id>:role/StackSnapRole"
              {...methods.register("assumedRoleArn", {
                required: true,
                validate: (v) =>
                  /^arn:aws[\w-]*:iam::\d{12}:role\/.+$/.test(v)
                    ? undefined
                    : "Please enter a valid IAM Role ARN",
              })}
              sizing={"sm"}
            />
            <CollapsibleSection
              collapsed
              placement={"bottom-right"}
              trigger={({ isOpen }) => (
                <span className={"text-sm text-blue-600 dark:text-blue-400"}>
                  {isOpen ? "Hide instructions" : "Create a new IAM Role"}
                </span>
              )}
              className={"mt-0"}
            >
              <Container className={"text-sm"}>
                <InstructionalStep title={"Step 1"}>
                  <CreateRoleStep externalId={externalId} />
                </InstructionalStep>
                <InstructionalStep title={"Step 2"}>
                  Assign your project's custom policy or an existing valid
                  policy to the IAM role you created in Step 1. If you have not
                  yet created a custom policy, create one using the permissions
                  below.
                  <CollapsibleSection
                    collapsed
                    collapsedText={"Show custom policy permissions"}
                    expandedText={"Hide custom policy permissions"}
                    color={mode}
                    size={"xs"}
                  >
                    <PolicyViewer text={project?.policy} color={mode} />
                  </CollapsibleSection>
                </InstructionalStep>
                <InstructionalStep title={"Step 3"}>
                  Copy the ARN of the role you created in Step 1 and paste it
                  into the field above.
                </InstructionalStep>
              </Container>
            </CollapsibleSection>
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
                    onClick={() =>
                      methods.setValue("region", region, {
                        shouldDirty: true,
                        shouldTouch: true,
                        shouldValidate: true,
                      })
                    }
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
        {isSubmitting ? "Saving" : "Save"}
      </Button>
    </form>
  );
};
