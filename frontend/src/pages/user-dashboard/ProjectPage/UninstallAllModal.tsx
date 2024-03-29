import { Button, Label, Modal, TextInput } from "flowbite-react";
import { useForm } from "react-hook-form";
import { useEffect, useState } from "react";
import { AiOutlineLoading } from "react-icons/ai";
import useApplicationStore from "../../store/ApplicationStore.ts";
import { UIError } from "../../../shared/errors.ts";
import { FormFooter } from "../../../components/FormFooter.tsx";
import type { WorkflowRunSummary } from "../../../shared/models/Workflow.ts";
import { useNavigate } from "react-router-dom";

interface UninstallAllModalProps {
  onClose: () => void;
  show?: boolean;
}

export interface UninstallAllFormState {
  confirmation: string;
  removeFromStack: boolean;
}

export default function UninstallAllModal({
  onClose,
  show,
}: UninstallAllModalProps) {
  const {
    reset,
    register,
    handleSubmit,
    watch,
    formState: { errors, isValid },
  } = useForm<UninstallAllFormState>();

  const { addError, uninstallProject } = useApplicationStore();
  const watchConfirmation = watch("confirmation");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const onSubmit = async () => {
    let success = false;
    setIsSubmitting(true);
    let response: WorkflowRunSummary | undefined;
    try {
      response = await uninstallProject();
      success = true;
    } catch (e: any) {
      addError(
        new UIError({
          errorId: "UninstallAllModal:Submit",
          message: `Uninstalling all apps failed`,
          messageComponent: <span>Uninstalling all apps failed!</span>,
          cause: e,
        }),
      );
    } finally {
      setIsSubmitting(false);
    }
    if (success) {
      onClose();
      if (response) {
        navigate(
          `/project/workflows/${response.workflow_type.toLowerCase()}/runs/${response.run_number}`,
        );
      }
    }
  };

  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        reset();
        onClose?.();
      }
    };
    window.addEventListener("keydown", handleEsc);

    return () => {
      window.removeEventListener("keydown", handleEsc);
    };
  }, [onClose, reset]);

  return (
    <Modal
      show={show !== false}
      onClose={() => {
        reset();
        onClose?.();
      }}
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        onReset={() => {
          reset();
          onClose?.();
        }}
      >
        <Modal.Header>Uninstall All Apps</Modal.Header>
        <Modal.Body>
          <div className={"flex flex-col gap-6"}>
            <p className={"mb-4 text-sm dark:text-white"}>
              Uninstalling all apps will remove all cloud resources and data
              associated with your entire stack.
            </p>

            <div>
              <div className="mb-2 block">
                <Label htmlFor="confirmation">
                  Type{" "}
                  <strong>
                    <i>uninstall</i>
                  </strong>{" "}
                  to confirm
                </Label>
              </div>
              <TextInput
                data-1p-ignore
                autoComplete="off"
                id="confirmation"
                {...register("confirmation", {
                  required: 'Please type "uninstall" to uninstall.',
                  validate: (value) => value === "uninstall",
                })}
                placeholder="uninstall"
                type="text"
                color={errors.confirmation ? "failure" : undefined}
                helperText={errors.confirmation?.message}
              />
            </div>
            {/*<div className="flex items-center gap-2">*/}
            {/*  <Checkbox {...register("removeFromStack")} id="removeFromStack" />*/}
            {/*  <Label htmlFor="removeFromStack">Remove from stack</Label>*/}
            {/*  <span className="text-xs text-gray-400 dark:text-gray-500">*/}
            {/*    <i>*/}
            {/*      (This will remove all apps and their configuration from your*/}
            {/*      stack.)*/}
            {/*    </i>*/}
            {/*  </span>*/}
            {/*</div>*/}
          </div>
        </Modal.Body>
        <Modal.Footer>
          <FormFooter>
            <div className="flex gap-2">
              <Button type="reset" color="clear" className="dark:text-white">
                Cancel
              </Button>
              <Button
                type="submit"
                color="purple"
                disabled={
                  Object.entries(errors).length > 0 ||
                  !watchConfirmation ||
                  isSubmitting ||
                  !isValid
                }
                isProcessing={isSubmitting}
                processingSpinner={
                  <AiOutlineLoading className="animate-spin" />
                }
              >
                Uninstall
              </Button>
            </div>
          </FormFooter>
        </Modal.Footer>
      </form>
    </Modal>
  );
}
