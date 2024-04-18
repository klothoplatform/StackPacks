import type { FC } from "react";
import React, { useEffect, useMemo, useState } from "react";
import { UIError } from "../shared/errors.ts";
import { ErrorBoundary } from "react-error-boundary";
import { FallbackRenderer } from "../components/FallbackRenderer.tsx";
import { trackError } from "./store/ErrorStore.ts";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Dropdown,
  HelperText,
  Label,
  TextInput,
  useThemeMode,
} from "flowbite-react";
import { MdChevronLeft } from "react-icons/md";
import useApplicationStore from "./store/ApplicationStore.ts";
import type { Project } from "../shared/models/Project.ts";
import {
  formStateToAppConfig,
  isProjectDeployed,
  toFormState,
} from "../shared/models/Project.ts";
import { FormProvider, useForm } from "react-hook-form";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import { awsDefaultRegions, awsRegions } from "../shared/aws-regions.ts";
import { CollapsibleSection } from "../components/CollapsibleSection.tsx";
import { CreateRoleStep } from "../components/CreateRoleStep.tsx";
import { Container } from "../components/Container.tsx";
import { InstructionalStep } from "../components/InstructionalStep.tsx";
import { PolicyViewer } from "../components/PolicyViewer.tsx";
import { DynamicConfigForm } from "../components/config/DynamicConfigForm.tsx";
import type { Stackpack } from "../shared/models/Stackpack.ts";
import { FormFooter } from "../components/FormFooter.tsx";
import { useEffectOnMount } from "../hooks/useEffectOnMount.ts";
import { WorkingOverlay } from "../components/WorkingOverlay.tsx";
import { ConfirmationModal } from "../components/ConfirmationModal.tsx";

export const ConfigureEnvironmentPage: FC = () => {
  const { project, getStackPacks } = useApplicationStore();
  const [stackPacks, setStackPacks] = useState<Map<string, Stackpack>>(
    new Map(),
  );
  const [isLoaded, setIsLoaded] = useState(false);

  const navigate = useNavigate();
  const { mode } = useThemeMode();

  useEffectOnMount(() => {
    (async () => {
      try {
        const packs = await getStackPacks(true);
        console.log("getting stack packs", packs);
        setStackPacks(packs);
      } catch (e) {
        trackError(
          new UIError({
            message: "Failed to load stack packs",
            errorId: "ConfigureEnvironmentPage:useEffectOnMount",
            cause: e,
          }),
        );
      } finally {
        setIsLoaded(true);
      }
    })();
  });

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
          {isLoaded ? (
            <ConfigureEnvironmentForm
              project={project}
              stackPacks={stackPacks}
            />
          ) : (
            <WorkingOverlay show inset message={"Loading Environment..."} />
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
};

interface ConfigureEnvironmentFormState {
  region: string;
  assumedRoleArn: string;
  assumedRoleExternalId: string;

  [key: string]: any;
}

const APP_CONFIG_PREFIX = "app_config";
export const ConfigureEnvironmentForm: FC<{
  project: Project;
  stackPacks: Map<string, Stackpack>;
}> = ({ project, stackPacks }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const { updateProject, addError, installProject } = useApplicationStore();
  const [externalId, setExternalId] = useState<string>(
    project.assumed_role_external_id || crypto.randomUUID(),
  );
  const { mode } = useThemeMode();

  useEffect(() => {
    setExternalId(project.assumed_role_external_id || crypto.randomUUID());
  }, [project.assumed_role_external_id]);

  const commonFormValues = useMemo(() => {
    const state = toFormState(
      project.stack_packs["common"]?.configuration,
      Object.values(stackPacks.get("common").configuration),
      "common",
    );
    return Object.fromEntries(
      Object.entries(state).map(([key, value]) => [
        `${APP_CONFIG_PREFIX}#${key}`,
        value,
      ]),
    );
  }, [project.stack_packs, stackPacks]);

  const methods = useForm<ConfigureEnvironmentFormState>({
    defaultValues: {
      region: project.region,
      assumedRoleArn: project.assumed_role_arn || "",
      assumedRoleExternalId: externalId,
      ...commonFormValues,
    },
  });

  const { isDirty, errors, dirtyFields } = methods.formState;

  const appConfigIsDirty = Object.keys(dirtyFields).some((key) =>
    key.startsWith(`${APP_CONFIG_PREFIX}#`),
  );

  const onConfirm = methods.handleSubmit(async (data) => {
    setIsSubmitting(true);
    try {
      const changedFields = Object.fromEntries(
        Object.entries(data).filter(([key]) => {
          if (dirtyFields[key]) {
            return true;
          }
          const keyParts = key.split("#");
          const partialKeys = [];
          for (let i = 1; i < keyParts.length; i++) {
            partialKeys.push(keyParts.slice(0, i).join("#"));
          }
          return partialKeys.some((k) =>
            Object.keys(dirtyFields).some((df) => df.startsWith(k)),
          );
        }),
      ) as Partial<ConfigureEnvironmentFormState>;

      let stackPackData = Object.fromEntries(
        Object.entries(changedFields).filter(([key]) =>
          key.startsWith(`${APP_CONFIG_PREFIX}#`),
        ),
      );
      stackPackData = Object.fromEntries(
        Object.entries(stackPackData).map(([key, value]) => [
          key.replace(/^[^#]*#/, ""),
          value,
        ]),
      );

      try {
        await updateProject({
          region: isProjectDeployed(project) ? undefined : changedFields.region,
          assumed_role_arn: changedFields.assumedRoleArn,
          assumed_role_external_id: changedFields.assumedRoleArn
            ? data.assumedRoleExternalId
            : undefined,
          configuration: Object.keys(stackPackData).length
            ? formStateToAppConfig(stackPackData, stackPacks)
            : undefined,
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

      if (appConfigIsDirty) {
        try {
          const response = await installProject();
          navigate(
            `/project/workflows/${response.workflow_type.toLowerCase()}/runs/${response.run_number}`,
          );
          return;
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
      }
      navigate("/project");
    } finally {
      setIsSubmitting(false);
    }
  });

  const [showConfirmation, setShowConfirmation] = useState(false);
  const onSubmit = async () => {
    if (appConfigIsDirty) {
      setShowConfirmation(true);
    } else {
      await onConfirm();
    }
  };

  const watchRegion = methods.watch("region");

  return (
    <form
      className={
        "dark:divide-gray-7000 mr-10 flex h-fit min-h-0 flex-col divide-y divide-gray-300 dark:divide-gray-700"
      }
    >
      <div className={"flex h-fit min-h-0 flex-col gap-2"}>
        <FormProvider {...methods}>
          <div className={"flex flex-col gap-1 p-1"}>
            <Label>Deployment Role ARN</Label>
            <TextInput
              helperText={
                errors.assumedRoleArn?.message ? (
                  <span className={"text-xs text-red-600 dark:text-red-400"}>
                    {errors.assumedRoleArn?.message}
                  </span>
                ) : undefined
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
          <div className={"flex flex-col gap-2 p-1"}>
            <Label>Region</Label>
            <div>
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
              {isProjectDeployed(project) && (
                <HelperText color={"gray"} className={"text-xs"}>
                  Region cannot be changed while your project is deployed.
                </HelperText>
              )}
            </div>
          </div>
          <DynamicConfigForm
            sections={[
              {
                title: "Common Configuration",
                prefix: APP_CONFIG_PREFIX,
                propertyMap: new Map([
                  [
                    "common",
                    Object.values(stackPacks.get("common").configuration),
                  ],
                ]),
                defaultOpened: true,
                flat: true,
              },
            ]}
          />
        </FormProvider>
      </div>
      <FormFooter className={"items-center pb-2 pt-4"}>
        {appConfigIsDirty && (
          <span className={"text-xs italic text-gray-500 dark:text-gray-400"}>
            Some configuration changes require a deployment to take effect.
          </span>
        )}
        <Button
          className={"w-fit whitespace-nowrap"}
          color={"purple"}
          onClick={onSubmit}
          isProcessing={isSubmitting}
          processingSpinner={
            <AiOutlineLoading3Quarters className="animate-spin" />
          }
          disabled={isSubmitting || !isDirty}
        >
          {isSubmitting
            ? "Saving"
            : `Save${appConfigIsDirty ? " and deploy" : ""}`}
        </Button>
      </FormFooter>
      <ConfirmationModal
        show={showConfirmation}
        onClose={() => setShowConfirmation(false)}
        title={"Save and Deploy Environment Changes"}
        prompt={
          <div className={"flex flex-col gap-6 dark:text-white"}>
            <p>
              Saving these changes will trigger a deployment of your project and
              may result in application downtime.
            </p>
            <p>Are you sure you want to proceed?</p>
          </div>
        }
        onConfirm={onConfirm}
        confirmButtonLabel={"Save and Deploy"}
      />
    </form>
  );
};
