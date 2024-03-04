import { trackError } from "../../pages/store/ErrorStore";

import { Button } from "flowbite-react";
import { FormProvider, useForm } from "react-hook-form";
import type { FC } from "react";
import React, { useEffect } from "react";

import useApplicationStore from "../../pages/store/ApplicationStore";

import { ErrorBoundary } from "react-error-boundary";
import { FallbackRenderer } from "../FallbackRenderer";
import { UIError } from "../../shared/errors";
import { resolveStackPacks } from "../../shared/models/StackPack.ts";
import type {
  ListProperty,
  MapProperty,
  Property,
} from "../../shared/configuration-properties.ts";
import { CollectionTypes } from "../../shared/configuration-properties.ts";
import { ConfigSection } from "./ConfigSection.tsx";
import { ConfigGroup } from "./ConfigGroup.tsx";
import { isCollection } from "yaml";

export interface ConfigFormSection {
  title: string;
  propertyMap: Map<string, Property[]>;
  defaultOpened?: boolean;
}

interface ConfigFormProps {
  sections?: ConfigFormSection[];
  showCustomConfig?: boolean;
}

export const ConfigForm: FC<ConfigFormProps> = ({ sections }) => {
  const { addError, stackPacks, onboardingWorkflowState } =
    useApplicationStore();

  const selectedStackPacks = resolveStackPacks(
    onboardingWorkflowState.selectedStackPacks,
    stackPacks,
  );

  const getSectionsState = (sections?: ConfigFormSection[]) => {
    if (!sections) {
      return {};
    }
    let stateMap: { [key: string]: {} } = {};
    sections.forEach((section) => {
      return section.propertyMap.forEach((properties, stackPackId): any => {
        const fs = toFormState(selectedStackPacks, properties, stackPackId);
        Object.keys(fs).forEach((key) => {
          stateMap[key] = fs[key];
        });
      });
    });
    return stateMap;
  };

  const methods = useForm({
    shouldFocusError: true,
    defaultValues: {
      ...getSectionsState(sections),
    },
  });

  const formState = methods.formState;
  const {
    defaultValues,
    dirtyFields,
    isSubmitted,
    isSubmitSuccessful,
    isDirty,
  } = formState;

  useEffect(() => {
    if (isSubmitted && !isSubmitSuccessful) {
      return;
    } else if (sections) {
      // methods.reset({
      //   ...getSectionsState(sections),
      // });
    }
  }, [getSectionsState, isSubmitSuccessful, isSubmitted, methods, sections]);

  return (
    <ErrorBoundary
      onError={(error, info) =>
        trackError(
          new UIError({
            message: "uncaught error in ConfigForm",
            errorId: "ConfigForm:ErrorBoundary",
            cause: error,
            data: { info },
          }),
        )
      }
      fallbackRender={FallbackRenderer}
    >
      <FormProvider {...methods}>
        <form
          className="flex size-full min-h-0 flex-col justify-between"
          onSubmit={methods.handleSubmit(() => alert("submitted"))}
        >
          <div className="mb-2 max-h-full min-h-0 w-full overflow-y-auto overflow-x-hidden pb-2 [&>*:not(:last-child)]:mb-2">
            {sections?.map((section, index) => {
              return (
                <ConfigSection
                  key={section.title}
                  id={section.title}
                  title={section.title}
                  removable={false}
                  defaultOpened={section.defaultOpened ?? true}
                >
                  {[...section.propertyMap.entries()].map(
                    ([stackPackId, properties]) => {
                      if (properties.length === 0) {
                        return null;
                      }

                      return (
                        <ConfigSection
                          key={stackPackId}
                          id={stackPackId}
                          title={stackPackId}
                        >
                          <ConfigGroup
                            stackPackId={stackPackId}
                            fields={properties}
                          />
                        </ConfigSection>
                      );
                    },
                  )}
                </ConfigSection>
              );
            })}
          </div>
          {isDirty && (
            <div className="flex flex-col gap-2 border-t border-gray-200 pt-2 dark:border-gray-700">
              <div className="flex justify-end gap-2">
                <Button outline color="" onClick={() => alert("cancel")}>
                  Cancel
                </Button>

                <Button type="submit" color="purple">
                  Save
                </Button>
              </div>
            </div>
          )}
        </form>
      </FormProvider>
    </ErrorBoundary>
  );
};

function toFormState(
  metadata: any,
  fields: Property[] = [],
  stackPackId?: string,
) {
  const formState: any = {};
  if (!metadata) {
    return formState;
  }

  const props = new Set([
    ...Object.keys(metadata),
    ...fields.map((f) => f.name),
  ]);

  props.forEach((property) => {
    let key = property;
    if (stackPackId) {
      key = `${stackPackId}#${property}`;
    }

    const value = metadata[property];
    const field = fields.find((field) => field.name === property);
    switch (field?.type) {
      case CollectionTypes.Map:
        if (!value) {
          formState[key] = [];
        } else if (isCollection((field as MapProperty).valueType)) {
          formState[key] = toFormState(value, field.properties);
        } else {
          formState[key] = Object.entries(value).map(([key, value]) => {
            return { key, value };
          });
        }
        break;
      case CollectionTypes.Set:
      case CollectionTypes.List:
        if (!value) {
          formState[key] = [];
          break;
        }
        formState[key] = value.map((value: any) => {
          if (isCollection((field as ListProperty).itemType)) {
            const inner = toFormState(value, field.properties);
            return Object.fromEntries(
              Object.entries(inner).map(([key, value]) => {
                // remove the resource id prefix from the key for nested fields
                return [key, value];
              }),
            );
          }
          return { value };
        });
        break;
      default:
        if (field) {
          formState[key] = value ?? null;
        }
    }
  });
  return formState;
}

/**
 getModifiedFormFields returns a map of qualified field name to value of all form fields that have been modified from their default values.
 each entry represents the deepest nested field that has been modified.
 only fields that are either primitive types or have primitive value/item types are considered.
 the qualified field name is the dot-separated path to the field from the root of the form. List and Set items are indexed by their position in the collection.
 the value is the primitive nested value of the field. if the field is a collection, the value is the nested value of the first item.
 */
function getModifiedFormFields(
  formFields: any,
  defaultValues: any,
  dirtyFields: any,
  stackPackId: string,
  resourceFields: Property[] = [],
  parentKey?: string,
): Map<string, any> {
  const modifiedFormFields = new Map<string, any>();
  Object.keys(dirtyFields).forEach((key) => {
    const prop = key.split("#", 2)[1] ?? key;
    const fieldValue = formFields?.[key];
    const defaultValue = defaultValues?.[key];
    const dirtyField = dirtyFields?.[key];
    const resourceField = resourceFields.find(
      (field) => field.name === prop.replaceAll(/\[\d+]/g, ""),
    );
    const qualifiedKey = parentKey ? `${parentKey}.${prop}` : key;
    if (!resourceField) {
      return;
    }
    if (fieldValue === undefined) {
      modifiedFormFields.set(qualifiedKey, undefined);
      return;
    }

    // ignore non-dirty fields
    if (!dirtyField || (Array.isArray(dirtyField) && !dirtyField.length)) {
      return;
    }

    if (resourceField.type === CollectionTypes.Map) {
      if (isCollection((resourceField as MapProperty).valueType)) {
        getModifiedFormFields(
          fieldValue,
          defaultValue,
          dirtyField,
          stackPackId,
          resourceField.properties,
          qualifiedKey,
        ).forEach((value, key) => {
          modifiedFormFields.set(key, value);
        });
      } else {
        dirtyField.forEach((item: any, index: number) => {
          if (!item?.["key"] && !item?.["value"]) {
            return;
          }
          modifiedFormFields.set(`${qualifiedKey}[${index}]`, {
            key: fieldValue[index]?.["key"],
            value: fieldValue[index]?.["value"],
          });
        });
      }
    } else if (
      resourceField.type === CollectionTypes.List ||
      resourceField.type === CollectionTypes.Set
    ) {
      if (isCollection((resourceField as ListProperty).itemType)) {
        dirtyField.forEach((_: any, index: number) => {
          const indexValue = fieldValue?.[index];
          if (indexValue === undefined) {
            modifiedFormFields.set(`${qualifiedKey}[${index}]`, undefined);
          }

          getModifiedFormFields(
            fieldValue?.[index],
            defaultValue?.[index],
            dirtyField[index],
            stackPackId,
            resourceField.properties,
            `${qualifiedKey}[${index}]`,
          ).forEach((value, key) => {
            modifiedFormFields.set(key, value);
          });
        });
      } else {
        dirtyField.forEach((item: any, index: number) => {
          if (!item?.["value"]) {
            return;
          }
          modifiedFormFields.set(`${qualifiedKey}[${index}]`, {
            value: fieldValue[index]?.["value"],
          });
        });
      }
    } else {
      modifiedFormFields.set(qualifiedKey, fieldValue);
    }
  });
  return modifiedFormFields;
}
