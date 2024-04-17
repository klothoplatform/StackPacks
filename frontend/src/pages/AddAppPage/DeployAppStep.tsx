import type { FC } from "react";
import React, { useState } from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Button } from "flowbite-react";
import { GrDeploy } from "react-icons/gr";
import useApplicationStore from "../store/ApplicationStore.ts";
import { AiOutlineLoading } from "react-icons/ai";
import { UIError } from "../../shared/errors.ts";
import { useNavigate } from "react-router-dom";
import { CostChange } from "../../components/CostChange.tsx";

export interface DeployAppStepProps extends StepperNavigatorProps {
  selectedApp: string;
}

export const DeployAppStep: FC<DeployAppStepProps> = ({
  selectedApp,
  ...props
}) => {
  const { installApp, addError, project } = useApplicationStore();
  const [installationState, setInstallationState] = useState<
    "initial" | "installing" | "installed" | "failed"
  >("initial");
  const navigate = useNavigate();

  const onDeploy = async () => {
    setInstallationState("installing");
    if (!project.region) {
      addError(
        new UIError({
          message: "Please select a region before deploying your stack.",
        }),
      );
      setInstallationState("initial");
      return;
    }

    try {
      const response = await installApp(selectedApp);
      setInstallationState("installed");
      navigate(
        `/project/apps/${response.app_id}/workflows/${response.workflow_type.toLowerCase()}/runs/${response.run_number}`,
      );
    } catch (e) {
      addError(
        new UIError({
          message: "Installation failed",
          cause: e,
        }),
      );
      setInstallationState("failed");
      return;
    }
  };

  const appName = project.stack_packs[selectedApp]?.display_name ?? selectedApp;

  return (
    <div className={"min-h-[50vh] w-full p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <div className={"flex size-full flex-col"}>
          <h3 className={"pb-4 text-xl font-medium dark:border-gray-700"}>
            Deploy {appName}
          </h3>
          <div className="flex size-full flex-col gap-6 overflow-y-auto px-2 pt-4">
            <div className={"flex flex-col gap-4"}>
              <p className={"text-sm"}>
                Deploy {appName} to the cloud. This will take a few minutes.
              </p>
              <div className={"flex flex-col gap-8"}>
                <Button
                  className={"size-fit whitespace-nowrap"}
                  color={"purple"}
                  size={"xl"}
                  processingSpinner={
                    <AiOutlineLoading className={"animate-spin"} />
                  }
                  disabled={installationState !== "initial"}
                  isProcessing={installationState === "installing"}
                  onClick={onDeploy}
                >
                  <span className={"flex items-center gap-2 "}>
                    <GrDeploy /> <span>Deploy</span>
                  </span>
                </Button>
                <CostChange
                  operation={"install"}
                  appIds={[selectedApp, "common"]}
                />
              </div>
            </div>
            <div className="ml-auto flex gap-4 justify-self-end">
              {installationState === "initial" && (
                <StepperNavigator {...props} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
