import type { FC } from "react";
import React, { useEffect } from "react";
import classNames from "classnames";
import { FaCheckCircle } from "react-icons/fa";
import { FaRegCircleDot } from "react-icons/fa6";
import { useStepper } from "../hooks/useStepper";
import type { Step } from "../context/StepperContext";
import { Button, useThemeMode } from "flowbite-react";

interface StepperProps {
  steps: Step[];
  activeStep?: number | string;
  currentStepColor?: string;
  currentStepIcon?: React.ReactNode;
  completedStepColor?: string;
  completedStepIcon?: React.ReactNode;
  uncompletedStepIcon?: React.ReactNode;
  colorTitle?: boolean;
}

export const Stepper: FC<StepperProps> = ({
  steps,
  activeStep,
  currentStepColor,
  currentStepIcon,
  completedStepColor,
  completedStepIcon,
  uncompletedStepIcon,
  colorTitle,
}) => {
  currentStepColor = currentStepColor || "blue";
  completedStepColor = completedStepColor || "green";
  currentStepIcon = currentStepIcon || <FaRegCircleDot />;
  completedStepIcon = completedStepIcon || <FaCheckCircle />;

  const { currentStep, setCurrentStep } = useStepper();

  useEffect(() => {
    const stepIndex = (id: string | number) =>
      typeof id === "number"
        ? (id as number)
        : steps.findIndex((step) => step.id === id);

    if (activeStep !== undefined) {
      setCurrentStep(stepIndex(activeStep));
    }
  }, [activeStep, setCurrentStep, steps]);

  const completedColors = `completed text-${completedStepColor}-600 dark:text-${completedStepColor}-500`;
  const currentColors = `current text-${currentStepColor}-600 dark:text-${currentStepColor}-500`;

  return (
    <ol className="flex w-full items-center justify-center text-center text-sm font-medium text-gray-500 dark:text-gray-400 sm:text-base">
      {steps.map((step, index) => (
        <li
          key={index}
          className={classNames(
            "flex items-center",
            {
              "text-gray-500 dark:text-gray-400": currentStep < index,
            },
            {
              "w-full after:border-gray-200 dark:after:border-gray-700 sm:after:inline-block after:hidden after:h-1 after:w-full after:border-b sm:after:content-[''] after:border-1 after:mx-3":
                index !== steps.length - 1,
              "w-fit": index === steps.length - 1,
            },
          )}
        >
          <span
            className={classNames("flex items-center whitespace-nowrap", {
              "after:mx-2 after:text-gray-200 after:content-['/'] dark:after:text-gray-500 sm:after:hidden":
                index !== steps.length - 1,
            })}
          >
            <span
              className={classNames("me-2", {
                [currentColors]: currentStep === index && !step.informational,
                [completedColors]:
                  currentStep > index ||
                  (currentStep === index && step.informational),
              })}
            >
              {step.titleIcon ? (
                step.titleIcon
              ) : (
                <>
                  {currentStep > index && completedStepIcon}
                  {!step.informational &&
                    currentStep === index &&
                    (currentStepIcon ? currentStepIcon : index + 1)}
                  {currentStep < index && (uncompletedStepIcon || index + 1)}
                </>
              )}
            </span>
            <span
              className={classNames({
                [currentColors]:
                  colorTitle && currentStep === index && !step.informational,
                [completedColors]:
                  colorTitle &&
                  (currentStep > index ||
                    (currentStep === index && step.informational)),
              })}
            >
              {step.title}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
};

export const TimelineStepper: FC<StepperProps> = ({
  steps,
  activeStep,
  currentStepColor,
  currentStepIcon,
  completedStepColor,
  completedStepIcon,
  uncompletedStepIcon,
  colorTitle,
}) => {
  currentStepColor = currentStepColor || "blue";
  completedStepColor = completedStepColor || "green";
  currentStepIcon = currentStepIcon || <FaRegCircleDot />;
  completedStepIcon = completedStepIcon || <FaCheckCircle />;

  const { currentStep, setCurrentStep } = useStepper();

  useEffect(() => {
    const stepIndex = (id: string | number) =>
      typeof id === "number"
        ? (id as number)
        : steps.findIndex((step) => step.id === id);

    if (activeStep !== undefined) {
      setCurrentStep(stepIndex(activeStep));
    }
  }, [activeStep, setCurrentStep, steps]);

  const completedColors = `completed text-${completedStepColor}-600 dark:text-${completedStepColor}-500`;
  const currentColors = `current text-${currentStepColor}-600 dark:text-${currentStepColor}-500`;

  return (
    <ol className="relative ml-2 h-fit border-s border-gray-200 text-gray-500 dark:border-gray-700 dark:text-gray-400">
      {steps.map((step, index) => (
        <li
          key={index}
          className={classNames("ms-6", {
            "text-gray-500 dark:text-gray-400": currentStep < index,
            "mb-10": index !== steps.length - 1,
          })}
        >
          <span className="absolute -start-2 flex items-center justify-center rounded-full bg-white ring-4 ring-white dark:bg-gray-900 dark:ring-gray-900">
            <span
              className={classNames({
                [currentColors]: currentStep === index && !step.informational,
                [completedColors]:
                  currentStep > index ||
                  (currentStep === index && step.informational),
              })}
            >
              {step.titleIcon ? (
                step.titleIcon
              ) : (
                <>
                  {currentStep > index && completedStepIcon}
                  {!step.informational &&
                    currentStep === index &&
                    (currentStepIcon ? currentStepIcon : index + 1)}
                  {currentStep < index && (uncompletedStepIcon || index + 1)}
                </>
              )}
            </span>
          </span>
          <h3
            className={classNames("font-medium leading-tight", {
              [currentColors]:
                colorTitle && currentStep === index && !step.informational,
              [completedColors]:
                colorTitle &&
                (currentStep > index ||
                  (currentStep === index && step.informational)),
            })}
          >
            {step.title}
          </h3>
          <p className="text-sm">{step.subtitle}</p>
        </li>
      ))}
    </ol>
  );
};

export interface StepperNavigatorProps {
  backDisabled?: boolean;
  nextDisabled?: boolean;
  goBack?: () => void;
  goForwards?: () => void;
  steps: Step[];
  currentStep: number;
}

export const StepperNavigator: FC<StepperNavigatorProps> = ({
  backDisabled,
  nextDisabled,
  goBack,
  goForwards,
  currentStep,
  steps,
}) => {
  const { mode } = useThemeMode();

  return (
    <div className="flex gap-2">
      {currentStep > 0 && (
        <Button
          color={mode}
          onClick={goBack}
          disabled={backDisabled || currentStep === 0}
        >
          Back
        </Button>
      )}
      {currentStep < steps.length - 1 && (
        <Button
          color={"purple"}
          onClick={goForwards}
          disabled={nextDisabled || currentStep === steps.length - 1}
        >
          Next
        </Button>
      )}
    </div>
  );
};
