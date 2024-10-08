import type { FC } from "react";
import React, { useState } from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Button, Dropdown } from "flowbite-react";
import { GrDeploy } from "react-icons/gr";
import useApplicationStore from "../store/ApplicationStore.ts";
import { AiOutlineLoading, AiOutlineLoading3Quarters } from "react-icons/ai";
import { UIError } from "../../shared/errors.ts";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { awsSupportedRegions, awsRegions } from "../../shared/aws-regions.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { InlineDropdown } from "../../components/InlineDropdown.tsx";
import { InstructionalStep } from "../../components/InstructionalStep.tsx";
import { CostChange } from "../../components/CostChange.tsx";

export interface DeploymentFormState {
  region: string;
}

export const DeploymentStep: FC<StepperNavigatorProps> = (props) => {
  const { installProject, addError, updateProject, project } =
    useApplicationStore();
  const [installationState, setInstallationState] = useState<
    "initial" | "installing" | "installed" | "failed"
  >("initial");
  const navigate = useNavigate();

  const defaultValues: DeploymentFormState = {
    region: project?.region,
  };

  const methods = useForm<DeploymentFormState>({ defaultValues });
  const watchRegion = methods.watch("region");
  const [updatingRegion, setUpdatingRegion] = useState(false);

  useEffectOnMount(() => {
    methods.register("region", {
      required: true,
    });

    methods.reset({
      region: defaultValues.region,
    });

    return () => {
      methods.unregister("region", {});
    };
  });

  const onSelectRegion = async (region: string) => {
    setUpdatingRegion(true);
    methods.setValue("region", region);
    try {
      if (project?.region !== region) {
        await updateProject({
          region,
        });
      }
    } finally {
      setUpdatingRegion(false);
    }
  };

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
      const response = await installProject();
      setInstallationState("installed");
      navigate(
        `/project/workflows/${response.workflow_type.toLowerCase()}/runs/${response.run_number}`,
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

  return (
    <div className={"min-h-[50vh] w-full p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <div className={"flex size-full flex-col"}>
          <h3 className={"pb-4 text-xl font-medium dark:border-gray-700"}>
            Deploy your project
          </h3>
          <div className="flex size-full flex-col gap-6 overflow-y-auto px-2 pt-4">
            <InstructionalStep title={"Step 1"}>
              <div className={"flex flex-col gap-4"}>
                <p className={"text-sm"}>
                  Select the AWS region where you want to deploy your project.
                </p>
                <div className={"flex items-center gap-2"}>
                  <InlineDropdown
                    disabled={updatingRegion}
                    color={"purple"}
                    prefix={"region"}
                    label={awsRegions[watchRegion] || "Select a region"}
                    placement={"bottom-start"}
                    size={"sm"}
                    theme={{
                      floating: {
                        base: "z-10 w-fit rounded divide-y divide-gray-100 shadow focus:outline-none max-h-48 overflow-y-auto",
                      },
                    }}
                  >
                    {Object.entries(awsSupportedRegions).map(
                      ([region, name]) => {
                        return (
                          <Dropdown.Item
                            key={region}
                            value={region}
                            onClick={() => onSelectRegion(region)}
                          >
                            {name}
                          </Dropdown.Item>
                        );
                      },
                    )}
                  </InlineDropdown>
                  {updatingRegion && (
                    <div
                      className={
                        "flex w-fit items-center gap-2 text-xs italic text-gray-500 dark:text-gray-400"
                      }
                    >
                      <span>Updating region...</span>
                      <AiOutlineLoading3Quarters
                        className={"animate-spin text-gray-200"}
                      />
                    </div>
                  )}
                </div>
              </div>
            </InstructionalStep>
            <InstructionalStep title={"Step 2"}>
              <div className={"flex flex-col gap-4"}>
                <p className={"text-sm"}>
                  Deploy your project to the cloud. This will take a few
                  minutes.
                </p>
                <div className={"flex flex-col gap-8"}>
                  <Button
                    className={"size-fit whitespace-nowrap"}
                    color={"purple"}
                    size={"xl"}
                    processingSpinner={
                      <AiOutlineLoading className={"animate-spin"} />
                    }
                    disabled={installationState !== "initial" || updatingRegion}
                    isProcessing={installationState === "installing"}
                    onClick={methods.handleSubmit(onDeploy)}
                  >
                    <span className={"flex items-center gap-2 "}>
                      <GrDeploy /> <span>Deploy</span>
                    </span>
                  </Button>
                  <CostChange
                    operation={"install"}
                    appIds={Object.keys(project.stack_packs)}
                  />
                </div>
              </div>
            </InstructionalStep>
            <div className="ml-auto flex gap-4 justify-self-end">
              {installationState === "initial" && (
                <StepperNavigator {...props} backDisabled={updatingRegion} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
