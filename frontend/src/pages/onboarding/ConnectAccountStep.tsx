import type { FC, PropsWithChildren } from "react";
import React from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Button, Card, TextInput } from "flowbite-react";
import { useForm } from "react-hook-form";
import { useStepper } from "../../hooks/useStepper.ts";
import { CollapsibleSection } from "../../components/CollapsibleSection.tsx";
import { MdContentCopy } from "react-icons/md";
import { RiExternalLinkLine } from "react-icons/ri";

export interface ConnectAccountFormState {
  awsRoleArn: string;
}

// TODO: make these configurable
const EXTERNAL_ID = "1234567890";
const AWS_ACCOUNT = "123456789012";
const MANAGED_POLICIES = [].map(encodeURIComponent).join("&policies=");

const samplePolicy = `{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:AttachVolume",
                "ec2:DetachVolume"
            ],
            "Resource": "arn:aws:ec2:*:*:instance/*",
            "Condition": {
                "StringEquals": {"aws:ResourceTag/Department": "Development"}
            }
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:AttachVolume",
                "ec2:DetachVolume"
            ],
            "Resource": "arn:aws:ec2:*:*:volume/*",
            "Condition": {
                "StringEquals": {"aws:ResourceTag/VolumeUser": "\${aws:username}"}
            }
        }
    ]
}`;

export const ConnectAccountStep: FC<StepperNavigatorProps> = (props) => {
  const methods = useForm<ConnectAccountFormState>({
    mode: "all",
    defaultValues: {
      awsRoleArn: "",
    },
  });

  const { isValid, errors } = methods.formState;

  const { goForwards } = useStepper();

  const completeStep = () => {
    try {
      methods.handleSubmit((data) => {
        console.log(data);
      });
    } catch (e) {
      console.error(e);
      return;
    }
    goForwards();
  };

  return (
    <Card className={"h-fit w-full overflow-hidden p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <h3 className={"pb-1 text-xl font-medium"}>Connect your AWS account</h3>
        <div className="flex size-full flex-col justify-between overflow-hidden border-t border-gray-200 pt-4 text-sm dark:border-gray-700">
          <div className="flex size-full flex-col gap-6 overflow-y-auto p-1">
            <p>
              Create an IAM role in your AWS account to enable StackPacks to
              deploy and manage stacks on your behalf.
            </p>
            <Step title="Step 1">
              <p>
                Create an IAM role in your AWS account using the link below.
              </p>

              <Button
                as={"a"}
                size={"xs"}
                target="_blank"
                rel="noopener noreferrer"
                href={`https://console.aws.amazon.com/iam/home#/roles/create?step=type&trustedEntityType=AWS_ACCOUNT&awsAccount=${AWS_ACCOUNT}&isThirdParty=true&externalId=${EXTERNAL_ID}${MANAGED_POLICIES ? "&policies=" + MANAGED_POLICIES : ""}`}
                color={"purple"}
                className={"size-fit items-center whitespace-nowrap"}
              >
                <span className={"flex items-center gap-1"}>
                  Create role <RiExternalLinkLine />
                </span>
              </Button>
            </Step>

            <Step title="Step 2" optional>
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
                  await navigator.clipboard.writeText(samplePolicy);
                }}
              >
                <div
                  className={
                    "gray-200 mx-4 h-fit overflow-y-auto whitespace-pre-wrap rounded-lg p-4 font-mono text-green-700 dark:bg-gray-700 dark:text-green-200"
                  }
                >
                  {samplePolicy}
                </div>
              </CollapsibleSection>
            </Step>
            <Step title={"Step 3"}>
              <p>
                Assign the custom policy or an existing policy to the IAM role
                you created in Step 1.
              </p>
            </Step>
            <Step title={"Step 4"}>
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
                  placeholder="aws:iam::<account-id>:role/StackPacksRole"
                  {...methods.register("awsRoleArn", {
                    required: true,
                    validate: (v) =>
                      /^arn:aws[\w-]*:iam::\d{12}:role\/.+$/.test(v)
                        ? undefined
                        : "Please enter a valid IAM Role ARN",
                  })}
                  helperText={
                    <span className={"text-red-600 dark:text-red-500"}>
                      {errors?.awsRoleArn?.message}
                    </span>
                  }
                />
              </div>
            </Step>
          </div>
          <div className="ml-auto mt-4 flex size-fit gap-4">
            <StepperNavigator
              {...props}
              nextDisabled={!isValid}
              goForwards={completeStep}
            />
          </div>
        </div>
      </div>
    </Card>
  );
};

const Step: FC<
  PropsWithChildren<{
    title: string;
    optional?: boolean;
  }>
> = ({ title, optional, children }) => {
  return (
    <div className={"flex flex-col gap-2"}>
      <h3
        className={"text-lg font-medium text-primary-500 dark:text-primary-400"}
      >
        {title}
        {optional && (
          <span className={"text-sm text-gray-500 dark:text-gray-400"}>
            {" (optional)"}
          </span>
        )}
      </h3>
      {children}
    </div>
  );
};
