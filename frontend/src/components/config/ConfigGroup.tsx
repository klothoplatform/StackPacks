import type { FC, ReactNode } from "react";
import { ConfigField } from "./ConfigField";
import type {
  MapProperty,
  Property,
} from "../../shared/configuration-properties.ts";
import { CollectionTypes } from "../../shared/configuration-properties.ts";

type ConfigGroupProps = {
  stackPackId?: string;
  qualifiedFieldId?: string;
  valueSelector?: string;
  fields?: Property[];
  hidePrefix?: boolean;
};

export const ConfigGroup: FC<ConfigGroupProps> = ({
  stackPackId,
  qualifiedFieldId,
  valueSelector,
  fields,
}) => {
  const rows: ReactNode[] = [];
  let resourceMetadata: any;

  // Make sure that all field names are fully qualified with the configResource prefix
  const prefix =
    qualifiedFieldId?.startsWith(`${stackPackId}#`) || stackPackId === undefined
      ? ""
      : `${stackPackId}#`;
  const addRow = (property: Property) => {
    if (resourceMetadata?.imported) {
      if (property.hidden === true) {
        return;
      }
    } else if (
      property.deployTime ||
      property.configurationDisabled ||
      property.hidden
    ) {
      return;
    }

    rows.push(
      <div key={rows.length} className="h-fit max-w-full p-1">
        <ConfigField
          // only show the resource if it isn't the one selected
          field={property}
          qualifiedFieldId={
            qualifiedFieldId
              ? `${prefix}${qualifiedFieldId}.${property.id}`
              : `${prefix}${property.qualifiedId}`
          }
          valueSelector={valueSelector}
          title={property.name}
          required={
            (property.required && !resourceMetadata?.imported) ||
            (property.required &&
              property.deployTime &&
              resourceMetadata?.imported)
          }
          disabled={
            property.configurationDisabled && !resourceMetadata?.imported
          }
        />
      </div>,
    );
  };

  fields
    ?.map((property) =>
      property.type === CollectionTypes.Map &&
      (property as MapProperty).valueType === CollectionTypes.Map
        ? property.properties?.map((child) => ({
            ...child,
            name: `${property.name}.${child.name}`,
          })) ?? property
        : property,
    )
    .flat()
    .sort((a, b) => a.name.localeCompare(b.name))
    .forEach((property: Property) => addRow(property));

  return <>{rows}</>;
};
