import type { FC } from "react";
import React, { useEffect } from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Button, Card, List, TextInput } from "flowbite-react";
import { useForm } from "react-hook-form";
import { useStepper } from "../../hooks/useStepper.ts";
import { CollapsibleSection } from "../../components/CollapsibleSection.tsx";
import { MdContentCopy } from "react-icons/md";
import { RiExternalLinkLine } from "react-icons/ri";
import useApplicationStore from "../store/ApplicationStore.ts";
import { env } from "../../shared/environment.ts";
import { UIError } from "../../shared/errors.ts";
import { InstructionalStep } from "../../components/InstructionalStep.tsx";

export interface ConnectAccountFormState {
  assumedRoleArn: string;
}

const MANAGED_POLICIES = [].map(encodeURIComponent).join("&policies=");

export const ConnectAccountStep: FC<StepperNavigatorProps> = (props) => {
  const {
    onboardingWorkflowState: { externalId },
    project,
    updateProject,
    addError,
  } = useApplicationStore();
  const { goForwards } = useStepper();
  const methods = useForm<ConnectAccountFormState>({
    mode: "all",
  });

  useEffect(() => {
    methods.reset({
      assumedRoleArn: project?.assumed_role_arn ?? "",
    });
  }, [methods, project?.assumed_role_arn]);

  const { isValid, errors, isDirty } = methods.formState;

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
          errorId: "ConnectAccountStep:Submit",
        }),
      );
      return;
    }
    goForwards();
  };

  return (
    <Card className={"h-fit w-full overflow-hidden p-4"}>
      <div
        onSubmit={methods.handleSubmit(completeStep)}
        className={"flex size-full flex-col dark:text-white"}
      >
        <h3 className={"pb-1 text-xl font-medium"}>Connect your AWS account</h3>
        <div className="flex size-full flex-col justify-between overflow-hidden border-t border-gray-200 pt-4 text-sm dark:border-gray-700">
          <div className="flex size-full flex-col gap-6 overflow-y-auto overflow-x-hidden p-1">
            <p>
              Create an IAM role in your AWS account to enable StackPacks to
              deploy and manage stacks on your behalf.
            </p>
            <InstructionalStep title="Step 1">
              <p>
                Create an IAM role in your AWS account using the link below.
              </p>

              <Button
                as={"a"}
                size={"xs"}
                target="_blank"
                rel="noopener noreferrer"
                href={`https://console.aws.amazon.com/iam/home#/roles/create?step=type&trustedEntityType=AWS_ACCOUNT&awsAccount=${env.awsAccountId}&isThirdParty=true&externalId=${externalId}${MANAGED_POLICIES ? "&policies=" + MANAGED_POLICIES : ""}`}
                color={"purple"}
                className={"size-fit items-center whitespace-nowrap"}
              >
                <span className={"flex items-center gap-1"}>
                  Create role <RiExternalLinkLine />
                </span>
              </Button>
              <br />
              <p>
                The following information will be prefilled for you. Please do
                not make any modifications to these fields.
              </p>
              <div className={"h-fit w-full px-2"}>
                <div
                  className={
                    "h-fit w-full rounded-lg bg-gray-100 p-4 dark:bg-gray-700"
                  }
                >
                  <List className={"text-gray-800 dark:text-gray-200"}>
                    <List.Item>
                      <span className={"font-medium"}>Trusted entity:</span>{" "}
                      <code>AWS Account</code>
                    </List.Item>
                    <List.Item>
                      <span className={"font-medium"}>Account ID:</span>{" "}
                      <code>{env.awsAccountId}</code>
                    </List.Item>
                    <List.Item>
                      <span className={"font-medium"}>External ID:</span>{" "}
                      <code>{externalId}</code>
                    </List.Item>
                    <List.Item>
                      <span className={"font-medium"}>Require MFA:</span>{" "}
                      <code>unchecked</code>
                    </List.Item>
                  </List>
                </div>
              </div>
            </InstructionalStep>

            <InstructionalStep title="Step 2">
              Create a custom policy for the IAM role with the following
              permissions and continue to Step 3.
              <CollapsibleSection
                color={"purple"}
                size={"xs"}
                collapsedText={
                  <div className={"flex items-center gap-2"}>
                    <MdContentCopy /> Copy permissions
                  </div>
                }
                expandedText={
                  <div className={"flex items-center gap-2"}>
                    <MdContentCopy /> Copy permissions
                  </div>
                }
                onExpand={async () => {
                  await navigator.clipboard.writeText(project.policy);
                }}
              >
                <div
                  className={
                    "gray-200 mx-4 max-h-80 overflow-y-auto whitespace-pre-wrap rounded-lg p-4 font-mono text-xs text-green-700 dark:bg-gray-700 dark:text-green-200"
                  }
                >
                  <code>{project.policy}</code>
                </div>
              </CollapsibleSection>
            </InstructionalStep>
            <InstructionalStep title={"Step 3"}>
              <p>
                Assign the custom policy or an existing policy to the IAM role
                you created in Step 1.
              </p>
            </InstructionalStep>
            <InstructionalStep title={"Step 4"}>
              <p>
                Open the role you created in Step 1 and copy its ARN into the
                field below.
              </p>
              <div className="mt-2 flex h-fit max-w-md flex-col gap-1">
                <label htmlFor="awsRoleArn" className={"text-sm font-medium"}>
                  Role ARN
                </label>
                <TextInput
                  type="text"
                  id="awsRoleArn"
                  placeholder="arn:aws:iam::<account-id>:role/StackPacksRole"
                  {...methods.register("assumedRoleArn", {
                    required: true,
                    validate: (v) =>
                      /^arn:aws[\w-]*:iam::\d{12}:role\/.+$/.test(v)
                        ? undefined
                        : "Please enter a valid IAM Role ARN",
                  })}
                  helperText={
                    <span className={"text-red-600 dark:text-red-500"}>
                      {errors?.assumedRoleArn?.message}
                    </span>
                  }
                />
              </div>
            </InstructionalStep>
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
    </Card>
  );
};
