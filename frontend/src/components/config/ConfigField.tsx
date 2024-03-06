import type { CheckboxProps, TextInputProps } from "flowbite-react";
import {
  Button,
  Checkbox,
  Dropdown,
  Label,
  TextInput,
  Tooltip,
  useThemeMode,
} from "flowbite-react";
import type { FC, PropsWithChildren } from "react";
import React, { Fragment, useEffect, useState } from "react";

import { type RegisterOptions, useFormContext } from "react-hook-form";

import { ListField } from "./ListField";
import { MapField } from "./MapField";

import classNames from "classnames";
import { BiChevronRight, BiSolidHand, BiSolidPencil } from "react-icons/bi";
import { env } from "../../shared/environment";
import { IoInformationCircleOutline } from "react-icons/io5";
import type {
  EnumProperty,
  ListProperty,
  MapProperty,
  NumberProperty,
  Property,
  StringProperty,
} from "../../shared/configuration-properties.ts";
import {
  CollectionTypes,
  PrimitiveTypes,
} from "../../shared/configuration-properties.ts";
import { findChildProperty } from "../../shared/object-util.ts";

export interface ConfigFieldProps {
  stackPackId?: string;
  // qualifiedFieldName is the qualified name of the field, including the stackpack id prefix
  // in the format `${stackPackId}#${fieldName}`.
  qualifiedFieldId: string;
  field: Property;
  title?: string;
  required?: boolean;
  disabled?: boolean;
  valueSelector?: string;
}

type InputProps = {
  field: Property;
  qualifiedFieldName: string;
  rules?: RegisterOptions;
  required?: boolean;
  error?: any;
  valueSelector?: string;
} & TextInputProps;

type TextProps = TextInputProps &
  ConfigFieldProps & {
    field: StringProperty;
  };

type NumberProps = {
  field: NumberProperty;
} & TextInputProps &
  ConfigFieldProps;

type BooleanProps = {
  error?: any;
  valueSelector?: string;
} & CheckboxProps &
  ConfigFieldProps;

type EnumProps = {
  field: EnumProperty;
  qualifiedFieldName: string;
  allowedValues?: string[];
  disabled?: boolean;
  required?: boolean;
  error?: any;
  valueSelector?: string;
};

export const ConfigField: FC<ConfigFieldProps> = ({
  field,
  qualifiedFieldId,
  title,
  required,
  valueSelector,
  ...props
}) => {
  const { type, configurationDisabled } = field;
  const { formState } = useFormContext();
  const { errors, touchedFields, dirtyFields, defaultValues } = formState;
  const id = qualifiedFieldId + (valueSelector ?? "");
  const error = findChildProperty(errors, id);
  const touched = findChildProperty(touchedFields, id);
  const dirty = findChildProperty(dirtyFields, id);

  let element: React.ReactElement;
  switch (type) {
    case PrimitiveTypes.String:
      element = (
        <StringField
          qualifiedFieldId={qualifiedFieldId}
          field={field}
          valueSelector={valueSelector}
          required={required}
          {...props}
          color={error ? "failure" : undefined}
          helperText={<InputHelperText error={error} />}
        />
      );
      break;
    case PrimitiveTypes.Number:
      element = (
        <NumberField
          qualifiedFieldId={qualifiedFieldId}
          field={field as NumberProperty}
          valueSelector={valueSelector}
          required={required}
          {...props}
          color={error ? "failure" : undefined}
          helperText={<InputHelperText error={error} />}
        />
      );
      break;
    case PrimitiveTypes.Integer:
      element = (
        <IntField
          qualifiedFieldId={qualifiedFieldId}
          field={field as NumberProperty}
          valueSelector={valueSelector}
          required={required}
          {...props}
          color={error ? "failure" : undefined}
          helperText={<InputHelperText error={error} />}
        />
      );
      break;
    case PrimitiveTypes.Boolean:
      element = (
        <BooleanField
          qualifiedFieldId={qualifiedFieldId}
          field={field}
          valueSelector={valueSelector}
          {...props}
          color={error ? "failure" : undefined}
          required={required}
          error={error}
        />
      );
      break;
    case CollectionTypes.List:
    case CollectionTypes.Set:
      element = (
        <ListField
          qualifiedFieldId={qualifiedFieldId}
          field={field as ListProperty}
          {...props}
        />
      );
      break;
    case CollectionTypes.Map:
      element = (
        <MapField
          qualifiedFieldId={qualifiedFieldId}
          field={field as MapProperty}
          {...props}
        />
      );
      break;
    case PrimitiveTypes.Enum:
      element = (
        <EnumField
          field={field as EnumProperty}
          qualifiedFieldName={qualifiedFieldId ?? "UNKNOWN-ENUM"}
          allowedValues={(field as EnumProperty).allowedValues}
          valueSelector={valueSelector}
          disabled={configurationDisabled}
          required={required}
          error={error}
          {...props}
        />
      );
      break;
    default:
      console.warn(`Unknown property type: ${type}`);
      element = <></>;
  }

  if (!title) {
    title = qualifiedFieldId || field.qualifiedId || "";
  }

  // const silenceRequired =
  //   (required || field.required) &&
  //   field.type === PrimitiveTypes.Enum &&
  //   defaultValues?.[qualifiedFieldId] !== undefined;

  // temporarily silencing required for all fields
  const silenceRequired = true;

  return (
    <>
      {type !== CollectionTypes.Map ||
      (field as MapProperty).valueType !== CollectionTypes.Map ? (
        <>
          <div className="flex flex-col gap-1">
            <Label
              title={title}
              htmlFor={qualifiedFieldId}
              className={"flex w-full"}
              color={error ? "failure" : "default"}
            >
              <div
                className={
                  "flex max-w-[95%] items-center gap-1 [&>span:first-child]:hidden"
                }
              >
                {title.split(".").map((part, index) => {
                  return (
                    <Fragment key={index}>
                      <span className="px-1">
                        <BiChevronRight />
                      </span>
                      <span
                        className={"w-fit overflow-hidden text-ellipsis "}
                        key={index}
                      >
                        {part}
                      </span>
                    </Fragment>
                  );
                })}
                {field.description && (
                  <Tooltip
                    content={
                      <div className="max-w-sm">{field.description}</div>
                    }
                  >
                    <IoInformationCircleOutline size={12} />
                  </Tooltip>
                )}
                {field.required && !silenceRequired && (
                  <div className={"text-red-600"}>*</div>
                )}
                {env.debug.has("config-state") && (
                  <div className={"flex flex-row"}>
                    {touched === true && (
                      <span className={"inline-flex text-blue-500"}>
                        <BiSolidHand />
                      </span>
                    )}
                    {dirty === true && (
                      <span className={"inline-flex  text-yellow-700"}>
                        <BiSolidPencil />
                      </span>
                    )}
                  </div>
                )}
              </div>
            </Label>
            {element}
          </div>
        </>
      ) : (
        element
      )}
    </>
  );
};

export const StringField: FC<TextProps> = ({
  qualifiedFieldId,
  field,
  valueSelector,
  ...rest
}) => {
  const [showValue, setShowValue] = useState(!field.secret);
  const { mode } = useThemeMode();

  return (
    <div className="flex w-full gap-2">
      <div className="w-full">
        <InputField
          field={field}
          className="w-full"
          qualifiedFieldName={qualifiedFieldId ?? field.qualifiedId}
          inputMode="text"
          type={showValue ? "text" : "password"}
          valueSelector={valueSelector}
          rules={{
            minLength: field.minLength
              ? {
                  value: field.minLength,
                  message: `${field.name} must be at least ${field.minLength} characters in length.`,
                }
              : undefined,
            maxLength: field.maxLength
              ? {
                  value: field.maxLength,
                  message: `${field.name} may be at most ${field.maxLength} characters in length.`,
                }
              : undefined,
          }}
          disabled={field.configurationDisabled}
          required={field.required}
          {...rest}
        />
      </div>
      {field.secret && (
        <Button
          color={mode}
          size={"xs"}
          className={"h-[34px] w-12 whitespace-nowrap"}
          onClick={() => setShowValue(!showValue)}
        >
          {showValue ? "Hide" : "Show"}
        </Button>
      )}
    </div>
  );
};

export const NumberField: FC<NumberProps> = ({
  qualifiedFieldId,
  field,
  valueSelector,
  ...rest
}) => {
  return (
    <InputField
      field={field}
      qualifiedFieldName={qualifiedFieldId ?? field.qualifiedId}
      inputMode="numeric"
      type="number"
      rules={{
        min: field.minValue
          ? {
              value: field.minValue,
              message: `${field.name} must be at least ${field.minValue}`,
            }
          : undefined,
        max: field.maxValue
          ? {
              value: field.maxValue,
              message: `${field.name} may not exceed ${field.maxValue}.`,
            }
          : undefined,
      }}
      valueSelector={valueSelector}
      disabled={field.configurationDisabled}
      required={field.required}
      // validate minValue and maxValue
      {...rest}
    />
  );
};

export const IntField: FC<NumberProps> = ({
  qualifiedFieldId,
  field,
  valueSelector,
  ...rest
}) => {
  return (
    <InputField
      field={field}
      qualifiedFieldName={qualifiedFieldId ?? field.qualifiedId}
      inputMode="numeric"
      type="number"
      step="1"
      rules={{
        min: field.minValue
          ? {
              value: field.minValue,
              message: `${field.name} must be at least ${field.minValue}`,
            }
          : undefined,
        max: field.maxValue
          ? {
              value: field.maxValue,
              message: `${field.name} may not exceed ${field.maxValue}.`,
            }
          : undefined,
      }}
      valueSelector={valueSelector}
      required={field.required}
      disabled={field.configurationDisabled}
      {...rest}
    />
  );
};

const InputField: FC<InputProps> = ({
  field,
  qualifiedFieldName,
  required,
  valueSelector,
  rules,
  error,
  ...rest
}) => {
  const { register } = useFormContext();
  const id = qualifiedFieldName + (valueSelector ?? "");
  return (
    // <div className="flex w-full flex-col">
    <TextInput
      sizing={"sm"}
      id={id}
      disabled={rest.disabled}
      color={error ? "failure" : "gray"}
      helperText={<InputHelperText error={error} />}
      {...rest}
      {...register(id, {
        required: required && `${field.name} is required.`,
        ...rules,
      })}
    />
    // </div>
  );
};

export const BooleanField: FC<BooleanProps> = ({
  qualifiedFieldId,
  field,
  valueSelector,
  ...props
}) => {
  const { register } = useFormContext();
  const { configurationDisabled } = field;
  const id = qualifiedFieldId + (valueSelector ?? "");
  return (
    <Checkbox
      id={id}
      disabled={configurationDisabled}
      {...props}
      {...register(id)}
    />
  );
};

export const EnumField: FC<EnumProps> = ({
  field,
  qualifiedFieldName,
  allowedValues,
  disabled,
  required,
  error,
  valueSelector,
}) => {
  const id = qualifiedFieldName + (valueSelector ?? "");
  const { register, unregister, setValue, watch, formState } = useFormContext();
  const { defaultValues } = formState;
  const onClick = (value: string | null) => {
    setValue(id, value, {
      shouldTouch: true,
      shouldDirty: true,
      shouldValidate: true,
    });
  };

  const silenceRequired = defaultValues?.[qualifiedFieldName] !== undefined;

  const watchValue = watch(id);

  useEffect(() => {
    register(
      id,
      silenceRequired
        ? undefined
        : {
            required: required && `${field.name} is required.`,
          },
    );
    return () => {
      unregister(id, { keepDefaultValue: true });
    };
  }, [
    field.name,
    id,
    qualifiedFieldName,
    register,
    required,
    silenceRequired,
    unregister,
  ]);

  return (
    <ErrorHelper error={error}>
      <Dropdown
        size={"xs"}
        className="max-h-[50vh] overflow-y-auto"
        id={qualifiedFieldName}
        color={"purple"}
        disabled={disabled}
        label={watchValue ?? "Select a value"}
      >
        {!required && (
          <Dropdown.Item className={"italic"} onClick={() => onClick(null)}>
            Select a value
          </Dropdown.Item>
        )}
        {allowedValues?.map((value: string) => {
          return (
            <Dropdown.Item key={value} onClick={() => onClick(value)}>
              {value}
            </Dropdown.Item>
          );
        })}
      </Dropdown>
    </ErrorHelper>
  );
};

export const ErrorHelper: FC<PropsWithChildren<{ error?: any }>> = ({
  error,
  children,
}) => {
  return error ? (
    <div
      className={classNames("flex flex-col gap-1", {
        "block w-full border disabled:cursor-not-allowed disabled:opacity-50 dark:bg-gray-700 dark:text-red-500 dark:placeholder-red-500 dark:border-red-500 p-2.5 border-red-500 text-red-900 placeholder-red-700 text-sm rounded-lg focus:ring-red-500 focus:border-red-500 focus:outline-none focus:ring-1":
          error,
      })}
    >
      {children}
      <div className="mt-2 block max-h-20 max-w-full overflow-auto text-sm text-red-600 dark:text-red-500">
        {error.root && <p>{error.root.message?.toString()}</p>}
        <p>{error.message?.toString()}</p>
      </div>
    </div>
  ) : (
    <>{children}</>
  );
};

export const InputHelperText: FC<{ error?: any }> = ({ error }) => {
  return (
    error?.message && (
      <span className={"block max-w-full overflow-auto"}>
        {error.message.toString()}
      </span>
    )
  );
};
