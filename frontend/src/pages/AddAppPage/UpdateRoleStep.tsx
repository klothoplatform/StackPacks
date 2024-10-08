import type { FC } from "react";
import React, { useEffect } from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { useForm } from "react-hook-form";
import { useStepper } from "../../hooks/useStepper.ts";
import { CollapsibleSection } from "../../components/CollapsibleSection.tsx";
import { MdContentCopy } from "react-icons/md";
import useApplicationStore from "../store/ApplicationStore.ts";
import { UIError } from "../../shared/errors.ts";
import { ExternalLinkWrapper } from "../../components/ExternalLinkWrapper.tsx";
import { PolicyViewer } from "../../components/PolicyViewer.tsx";
import { useThemeMode } from "flowbite-react";

export interface ConnectAccountFormState {
  assumedRoleArn: string;
}

export const UpdateRoleStep: FC<StepperNavigatorProps> = (props) => {
  const {
    onboardingWorkflowState: { externalId },
    project,
    updateProject,
    addError,
  } = useApplicationStore();
  const { goForwards } = useStepper();
  const { mode } = useThemeMode();
  const methods = useForm<ConnectAccountFormState>({
    mode: "all",
  });

  useEffect(() => {
    methods.reset({
      assumedRoleArn: project?.assumed_role_arn ?? "",
    });
  }, [methods, project?.assumed_role_arn]);

  const { isValid, isDirty } = methods.formState;

  const completeStep = async (data: ConnectAccountFormState) => {
    if (!isDirty) {
      goForwards();
      return;
    }

    try {
      console.log(data);
      await updateProject({
        assumed_role_arn: data.assumedRoleArn,
        assumed_role_external_id: externalId,
      });
    } catch (e) {
      addError(
        new UIError({
          message: "An error occurred while updating your stack's IAM Role.",
          cause: e,
          errorId: "UpdateRoleStep:Submit",
        }),
      );
      return;
    }
    goForwards();
  };

  return (
    <div className={"h-fit w-full overflow-hidden p-4"}>
      <div
        onSubmit={methods.handleSubmit(completeStep)}
        className={"flex size-full flex-col dark:text-white"}
      >
        <h3 className={"pb-1 text-xl font-medium"}>
          Update AWS deployment role permissions
        </h3>
        <div className="flex size-full flex-col justify-between overflow-hidden pt-4 text-sm dark:border-gray-700">
          <div className="flex size-full flex-col gap-6 overflow-y-auto overflow-x-hidden px-4 py-1">
            <p>
              Update the permissions of the AWS IAM role that StackSnap uses to
              deploy your project to ensure that it has the necessary
              permissions to create resources required by any newly added
              applications in your AWS account.
            </p>
            <CollapsibleSection
              color={"purple"}
              size={"xs"}
              collapsed={true}
              collapsedText={
                <div className={"flex items-center gap-2"}>
                  <MdContentCopy /> Copy permissions
                </div>
              }
              expandedText={
                <div className={"flex items-center gap-2"}>
                  <MdContentCopy /> Hide permissions
                </div>
              }
              onExpand={async () => {
                await navigator.clipboard.writeText(project.policy);
              }}
            >
              <div className={"w-fit"}>
                <PolicyViewer text={project?.policy} color={mode} />
              </div>
            </CollapsibleSection>
            <ExternalLinkWrapper>
              <a
                target="_blank"
                rel="noopener noreferrer"
                href={"https://console.aws.amazon.com/iam/home#/policies"}
              >
                Go to IAM policy management console
              </a>
            </ExternalLinkWrapper>
          </div>
          <div className="ml-auto mt-4 flex size-fit gap-4">
            <StepperNavigator
              {...props}
              nextDisabled={!isValid}
              goForwards={methods.handleSubmit(completeStep)}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
