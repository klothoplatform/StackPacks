import type { FC } from "react";
import { useState } from "react";
import React from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Button, Card } from "flowbite-react";
import { GrDeploy } from "react-icons/gr";
import useApplicationStore from "../store/ApplicationStore.ts";
import { AiOutlineLoading } from "react-icons/ai";
import { UIError } from "../../shared/errors.ts";
import { useNavigate } from "react-router-dom";

export const DeploymentStep: FC<StepperNavigatorProps> = (props) => {
  const { installStack, addError } = useApplicationStore();
  const [deploymentState, setDeploymentState] = useState<
    "initial" | "installing" | "installed" | "failed"
  >("initial");
  const navigate = useNavigate();

  const onDeploy = async () => {
    setDeploymentState("installing");
    try {
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
          <h3 className={"pb-1 text-xl font-medium"}>Deploy your stack</h3>
          <div className="flex size-full w-full flex-col justify-between border-t border-gray-200 pt-4 dark:border-gray-700">
            <div
              className={
                "flex size-full flex-col items-center justify-center gap-6"
              }
            >
              <p className={"mb-6"}>
                Deploy your stack to the cloud. This will take a few minutes.
              </p>
              <Button
                className={"size-fit whitespace-nowrap"}
                color={"purple"}
                size={"xl"}
                processingSpinner={
                  <AiOutlineLoading className={"animate-spin"} />
                }
                isProcessing={deploymentState === "installing"}
                onClick={onDeploy}
              >
                <span className={"flex items-center gap-2 "}>
                  <GrDeploy /> <span>Deploy</span>
                </span>
              </Button>
            </div>
            <div className="ml-auto flex gap-4 justify-self-end">
              {deploymentState === "initial" && <StepperNavigator {...props} />}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
