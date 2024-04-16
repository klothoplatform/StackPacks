import { Button, Label, Modal, TextInput } from "flowbite-react";
import { useForm } from "react-hook-form";
import type { FC, ReactNode } from "react";
import { useEffect, useState } from "react";
import { AiOutlineLoading } from "react-icons/ai";
import { FormFooter } from "./FormFooter.tsx";

interface ConfirmationModalProps {
  onClose: () => void;
  show?: boolean;
  title: ReactNode;
  prompt: ReactNode | string;
  confirmButtonLabel?: string;
  cancelable?: boolean;
  confirmationText?: string;
  onConfirm: () => void | boolean | Promise<void | boolean>;
}

export interface ConfirmationFormState {
  confirmation: string;
}

export const ConfirmationModal: FC<ConfirmationModalProps> = ({
  onClose,
  show,
  title,
  prompt,
  confirmButtonLabel,
  cancelable = true,
  confirmationText,
  onConfirm,
}) => {
  const {
    reset,
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ConfirmationFormState>();

  const watchConfirmation = watch("confirmation");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const onSubmit = async () => {
    let success = false;
    setIsSubmitting(true);
    try {
      let result = onConfirm();
      if (result instanceof Promise) {
        result = await result;
      }
      success = result !== false;
    } finally {
      setIsSubmitting(false);
    }
    if (success) {
      onClose();
    }
  };

  useEffect(() => {
    if (!cancelable) {
      return;
    }

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
  }, [cancelable, onClose, reset]);

  return (
    <Modal
      dismissible={cancelable !== false}
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
        {title && <Modal.Header>{title}</Modal.Header>}
        <Modal.Body>
          <div className={"flex flex-col gap-6"}>
            {!!prompt && typeof prompt === "string" ? (
              <p className={"dark:text-white"}>{prompt}</p>
            ) : (
              <div>{prompt}</div>
            )}
            {!!confirmationText && (
              <div>
                <div className="mb-2 block">
                  <Label htmlFor="confirmation">
                    Type{" "}
                    <strong>
                      <i>{confirmationText}</i>
                    </strong>{" "}
                    to confirm
                  </Label>
                </div>
                <TextInput
                  data-1p-ignore
                  autoComplete="off"
                  id="confirmation"
                  {...register("confirmation", {
                    required: `Please type "${confirmationText}" to confirm.`,
                    validate: (value) => value === confirmationText,
                  })}
                  placeholder={confirmationText}
                  type="text"
                  color={errors.confirmation ? "failure" : undefined}
                  helperText={errors.confirmation?.message}
                />
              </div>
            )}
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
                  (confirmationText && !watchConfirmation) ||
                  isSubmitting
                }
                isProcessing={isSubmitting}
                processingSpinner={
                  <AiOutlineLoading className="animate-spin" />
                }
              >
                {confirmButtonLabel || "Confirm"}
              </Button>
            </div>
          </FormFooter>
        </Modal.Footer>
      </form>
    </Modal>
  );
};
