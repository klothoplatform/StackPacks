import type { FC } from "react";
import React from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Badge, Card, TextInput } from "flowbite-react";
import { useForm } from "react-hook-form";
import { useStepper } from "../../hooks/useStepper.ts";

export interface ConnectAccountFormState {
  awsRoleArn: string;
}

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
    <Card className={"h-fit w-full p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <h3 className={"pb-1 text-xl font-medium"}>Connect your AWS account</h3>
        <div className="flex size-full w-full flex-col justify-between border-t border-gray-200 pt-4 text-sm dark:border-gray-700">
          <div className="flex h-fit w-full flex-col gap-4">
            <p className={"mx-auto size-fit"}>
              StackPacks' AWS integration requires creating an
              <Badge
                className={"mx-2 inline-flex size-fit whitespace-nowrap"}
                size={"xs"}
                color={"gray"}
              >
                IAM Role
              </Badge>
              in your AWS account. The IAM role allows StackPacks to perform
              read-only (Get, List, and Describe) access for the metadata of AWS
              services.
            </p>
            <h3 className={"text-lg font-medium"}>Before you begin</h3>
            <ul className={"list-inside list-disc space-y-1"}>
              <li>
                Log in to your desired AWS account with permission to create IAM
                AWS resources
              </li>
              <li>More instructions for setting up the role...</li>
              <li>Paste the role ARN into the text box below</li>
            </ul>
            <div className="flex max-w-md flex-col gap-1">
              <label htmlFor="awsRoleArn" className={"text-sm"}>
                AWS Role ARN
              </label>
              {/*<form*/}
              {/*  onSubmit={(e) => {*/}
              {/*    e.preventDefault();*/}
              {/*    completeStep();*/}
              {/*  }}*/}
              {/*>*/}
              <TextInput
                type="text"
                id="awsRoleArn"
                placeholder="aws:iam::<account-id>:role/StackPacksRole"
                {...methods.register("awsRoleArn", {
                  required: true,
                  validate: (v) =>
                    /^arn:aws:iam::\d{12}:role\/[\w-]+$/.test(v)
                      ? undefined
                      : "Please enter a valid IAM Role ARN",
                })}
                helperText={
                  <span className={"text-red-600 dark:text-red-500"}>
                    {errors?.awsRoleArn?.message}
                  </span>
                }
              />
              {/*</form>*/}
            </div>
          </div>
          <div className="ml-auto mt-4 flex gap-4">
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
