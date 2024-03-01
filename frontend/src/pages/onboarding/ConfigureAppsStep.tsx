import type { FC } from "react";
import React, { useEffect } from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Card, Dropdown } from "flowbite-react";
import useApplicationStore from "../store/ApplicationStore.ts";
import { useForm } from "react-hook-form";
import { awsRegions } from "../../shared/aws-regions.ts";

export interface ConfigureStackFormState {
  region: string;
}

const defaultValues: ConfigureStackFormState = {
  region: "us-east-1",
};

export const ConfigureAppsStep: FC<StepperNavigatorProps> = ({
  goForwards,
  ...props
}) => {
  const { onboardingWorkflowState, updateOnboardingWorkflowState } =
    useApplicationStore();

  const methods = useForm<ConfigureStackFormState>({ defaultValues });
  const watchRegion = methods.watch("region");

  useEffect(() => {
    methods.register("region", {
      required: true,
    });

    methods.reset({
      region: onboardingWorkflowState.region || defaultValues.region,
    });

    return () => {
      methods.unregister("region", {});
    };
  }, []);

  const completeStep = (data: ConfigureStackFormState) => {
    console.log(data);
    updateOnboardingWorkflowState({
      region: data.region,
    });
    goForwards();
  };

  return (
    <Card className={"min-h-[50vh] w-full p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <div className={"flex size-full flex-col"}>
          <h3 className={"pb-1 text-xl font-medium"}>Configure your stack</h3>
          <div className="flex size-full w-full flex-col justify-between border-t border-gray-200 pt-4 dark:border-gray-700">
            <p></p>
            <Dropdown
              color={"purple"}
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
            </Dropdown>
            <div className="ml-auto flex gap-4 justify-self-end">
              <StepperNavigator
                {...props}
                goForwards={methods.handleSubmit(completeStep)}
              />
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
