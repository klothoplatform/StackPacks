import type { FC } from "react";
import React from "react";
import type { StepperNavigatorProps } from "../../components/Stepper.tsx";
import { StepperNavigator } from "../../components/Stepper.tsx";
import { Card } from "flowbite-react";

export const ConfigureAppsStep: FC<StepperNavigatorProps> = (props) => {
  return (
    <Card className={"min-h-[50vh] w-full p-4"}>
      <div className={"flex size-full flex-col dark:text-white"}>
        <div className={"flex size-full flex-col"}>
          <h3 className={"pb-1 text-xl font-medium"}>Configure your stack</h3>
          <div className="flex size-full w-full flex-col justify-between border-t border-gray-200 pt-4 dark:border-gray-700">
            <p></p>
            <div className="ml-auto flex gap-4 justify-self-end">
              <StepperNavigator {...props} />
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};
