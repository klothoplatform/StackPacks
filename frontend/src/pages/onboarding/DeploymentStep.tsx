import type { FC } from "react";
import { useState } from "react";
import React from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Button, Card, Dropdown } from "flowbite-react";
import { GrDeploy } from "react-icons/gr";
import useApplicationStore from "../store/ApplicationStore.ts";
import { AiOutlineLoading } from "react-icons/ai";
import { UIError } from "../../shared/errors.ts";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { awsRegions } from "../../shared/aws-regions.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { InlineDropdown } from "../../components/InlineDropdown.tsx";
import { InstructionalStep } from "../../components/InstructionalStep.tsx";

export interface DeploymentFormState {
  region: string;
}

const defaultValues: DeploymentFormState = {
  region: "us-east-1",
};

export const DeploymentStep: FC<StepperNavigatorProps> = (props) => {
  const {
    installStack,
    addError,
    onboardingWorkflowState,
    updateOnboardingWorkflowState,
    updateStack,
  } = useApplicationStore();
  const [deploymentState, setDeploymentState] = useState<
    "initial" | "installing" | "installed" | "failed"
  >("initial");
  const navigate = useNavigate();

  const methods = useForm<DeploymentFormState>({ defaultValues });
  const watchRegion = methods.watch("region");

  useEffectOnMount(() => {
    methods.register("region", {
      required: true,
    });

    methods.reset({
      region: onboardingWorkflowState.region || defaultValues.region,
    });

    return () => {
      methods.unregister("region", {});
    };
  });

  const onDeploy = async (data: DeploymentFormState) => {
    setDeploymentState("installing");

    updateOnboardingWorkflowState({
      region: data.region,
    });

    try {
      await updateStack({
        region: data.region,
      });
      await installStack();
    } catch (e) {
      addError(
        new UIError({
          message: "Deployment failed",
          cause: e,
        }),
      );
      setDeploymentState("failed");
      return;
    }
    setDeploymentState("installed");
    navigate("/user/dashboard");
  };

  return (
    <Card className={"min-h-[50vh] w-full p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <div className={"flex size-full flex-col"}>
          <h3
            className={
              "border-b border-gray-200 pb-4 text-xl font-medium dark:border-gray-700"
            }
          >
            Deploy your stack
          </h3>
          <div className="flex h-fit w-full flex-col gap-6 overflow-y-auto pt-4">
            <InstructionalStep title={"Step 1"}>
              <div className={"flex flex-col gap-4"}>
                <p className={"text-sm"}>
                  Select the AWS region where you want to deploy your stack.
                </p>
                <InlineDropdown
                  color={"purple"}
                  prefix={"region"}
                  label={awsRegions[watchRegion]}
                  placement={"bottom-start"}
                  size={"sm"}
                  theme={{
                    floating: {
                      base: "z-10 w-fit rounded divide-y divide-gray-100 shadow focus:outline-none max-h-48 overflow-y-auto",
                    },
                  }}
                >
                  {Object.entries(awsRegions).map(([region, name]) => {
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
                </InlineDropdown>
              </div>
            </InstructionalStep>

            <InstructionalStep title={"Step 2"}>
              <div className={"flex flex-col gap-4"}>
                <p className={"text-sm"}>
                  Deploy your stack to the cloud. This will take a few minutes.
                </p>
                <Button
                  className={"size-fit whitespace-nowrap"}
                  color={"purple"}
                  size={"xl"}
                  processingSpinner={
                    <AiOutlineLoading className={"animate-spin"} />
                  }
                  disabled={deploymentState !== "initial"}
                  isProcessing={deploymentState === "installing"}
                  onClick={methods.handleSubmit(onDeploy)}
                >
                  <span className={"flex items-center gap-2 "}>
                    <GrDeploy /> <span>Deploy</span>
                  </span>
                </Button>
              </div>
            </InstructionalStep>
          </div>
          <div className="ml-auto flex gap-4 justify-self-end">
            {deploymentState === "initial" && <StepperNavigator {...props} />}
          </div>
        </div>
      </div>
    </Card>
  );
};
