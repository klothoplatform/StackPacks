import type { FC, ReactNode } from "react";
import { ConfigField } from "./ConfigField";
import type {
  MapProperty,
  Property,
} from "../../shared/configuration-properties.ts";
import { CollectionTypes } from "../../shared/configuration-properties.ts";

type ConfigGroupProps = {
  prefix?: string;
  qualifiedFieldId?: string;
  valueSelector?: string;
  fields?: Property[];
  hidePrefix?: boolean;
};

export const ConfigGroup: FC<ConfigGroupProps> = ({
  prefix,
  qualifiedFieldId,
  valueSelector,
  fields,
}) => {
  const rows: ReactNode[] = [];

  // Make sure that all field names are fully qualified with the configResource prefix
  prefix =
    qualifiedFieldId?.startsWith(`${prefix}#`) || prefix === undefined
      ? ""
      : `${prefix}#`;
  const addRow = (property: Property) => {
    if (
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
          required={property.required}
          disabled={property.configurationDisabled}
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
