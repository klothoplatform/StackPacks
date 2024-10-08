import { Button, Label, Modal, TextInput } from "flowbite-react";
import { useForm } from "react-hook-form";
import React, { useEffect, useState } from "react";
import { AiOutlineLoading } from "react-icons/ai";
import useApplicationStore from "../store/ApplicationStore.ts";
import { UIError } from "../../shared/errors.ts";
import { FormFooter } from "../../components/FormFooter.tsx";
import { useNavigate } from "react-router-dom";
import type { WorkflowRunSummary } from "../../shared/models/Workflow.ts";
import { CostChange } from "../../components/CostChange.tsx";

interface UninstallAppModalProps {
  onClose: () => void;
  show?: boolean;
  id: string;
  name?: string;
}

export interface UninstallAppFormState {
  confirmation: string;
  removeFromStack: boolean;
}

export default function UninstallAppModal({
  onClose,
  show,
  id,
  name,
}: UninstallAppModalProps) {
  const {
    reset,
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<UninstallAppFormState>();

  const { addError, uninstallApp, project } = useApplicationStore();
  const watchConfirmation = watch("confirmation");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();

  const onSubmit = async () => {
    let success = false;
    setIsSubmitting(true);
    let response: WorkflowRunSummary | undefined;
    try {
      response = await uninstallApp(id);
      success = true;
    } catch (e: any) {
      addError(
        new UIError({
          errorId: "UninstallAppModal:Submit",
          message: `Uninstalling ${name} failed`,
          messageComponent: (
            <span>
              Uninstalling <strong>{name}</strong> failed!
            </span>
          ),
          cause: e,
          data: {
            id,
          },
        }),
      );
    } finally {
      setIsSubmitting(false);
    }
    if (success) {
      onClose();
      if (response) {
        navigate(
          `/project/apps/${response.app_id}/workflows/${response.workflow_type.toLowerCase()}/runs/${response.run_number}`,
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
        <Modal.Header>Uninstall "{name}"</Modal.Header>
        <Modal.Body>
          <div className={"flex flex-col gap-6"}>
            <p className={"mb-4 text-sm dark:text-white"}>
              Uninstalling <strong>{name}</strong> will remove all cloud
              resources and data associated with it.
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

            <CostChange operation={"uninstall"} appIds={[id]} />
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
                  isSubmitting
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
