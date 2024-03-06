import type { FC } from "react";
import React from "react";
import { useFieldArray, useFormContext } from "react-hook-form";
import { Textarea } from "flowbite-react";
import type { ConfigFieldProps } from "./ConfigField";
import { ConfigSection } from "./ConfigSection";
import { ConfigGroup } from "./ConfigGroup";
import { PrimitiveTable } from "./PrimitiveTable";
import type { MapProperty } from "../../shared/configuration-properties.ts";
import {
  CollectionTypes,
  PrimitiveTypes,
} from "../../shared/configuration-properties.ts";

type MapProps = ConfigFieldProps & {
  field: MapProperty;
  removable?: boolean;
};

export const MapField: FC<MapProps> = ({
  qualifiedFieldId,
  field,
  removable,
  disabled,
}) => {
  qualifiedFieldId = qualifiedFieldId ?? "UNKNOWN-MAP";

  const { register, control } = useFormContext();
  const { configurationDisabled, keyType, valueType } = field as MapProperty;

  useFieldArray({
    control,
    name: qualifiedFieldId,
    rules: {
      required:
        field.required && `${qualifiedFieldId.split(".").pop()} is required.`,
      minLength: field.minLength
        ? {
            value: field.minLength,
            message: `${qualifiedFieldId} must have at least ${field.minLength} entries.`,
          }
        : undefined,
      maxLength: field.maxLength
        ? {
            value: field.maxLength,
            message: `${qualifiedFieldId} may have at most ${field.maxLength} entries.`,
          }
        : undefined,
      validate: {
        uniqueKeys: (items: any[]) => {
          if (!items?.length) {
            return true;
          }
          if (field.uniqueKeys && !field.properties?.length) {
            const uniqueKeys = new Set();
            for (const item of items) {
              const key = JSON.stringify(item.key);
              if (uniqueKeys.has(key)) {
                return `${qualifiedFieldId} must have unique keys.`;
              }
              uniqueKeys.add(key);
            }
          }
          return true;
        },
      },
    },
  });

  if (
    keyType === PrimitiveTypes.String &&
    valueType === PrimitiveTypes.String
  ) {
    return (
      <PrimitiveTable
        id={qualifiedFieldId}
        disabled={configurationDisabled || disabled}
        properties={["key", "value"]}
      />
    );
  }
  if (keyType === PrimitiveTypes.String && valueType === CollectionTypes.Map) {
    return (
      <ConfigSection
        id={qualifiedFieldId}
        title={field.qualifiedId}
        removable={removable}
      >
        <ConfigGroup
          qualifiedFieldId={qualifiedFieldId}
          fields={field.properties}
          hidePrefix
        />
      </ConfigSection>
    );
  }

  return (
    <Textarea
      id={qualifiedFieldId}
      disabled={configurationDisabled}
      {...register(qualifiedFieldId ?? "")}
    />
  );
};
