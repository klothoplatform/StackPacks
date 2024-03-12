import { trackError } from "../../pages/store/ErrorStore";
import type { FC } from "react";
import React from "react";

import { ErrorBoundary } from "react-error-boundary";
import { FallbackRenderer } from "../FallbackRenderer";
import { UIError } from "../../shared/errors";
import type { Property } from "../../shared/configuration-properties.ts";
import { ConfigSection } from "./ConfigSection.tsx";
import { ConfigGroup } from "./ConfigGroup.tsx";

export interface DynamicSection {
  title: string;
  propertyMap: Map<string, Property[]>;
  defaultOpened?: boolean;
  flat?: boolean;
}

interface DynamicConfigFormProps {
  sections?: DynamicSection[];
}

export const DynamicConfigForm: FC<DynamicConfigFormProps> = ({ sections }) => {
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
      <div className="size-fit min-h-0 w-full pb-2 [&>*:not(:last-child)]:mb-2">
        {sections?.map((section, index) => {
          if (section.flat) {
            return [...section.propertyMap.entries()].map(
              ([stackPackId, properties], index) => {
                if (properties.length === 0) {
                  return null;
                }
                return (
                  <ConfigGroup
                    key={index}
                    stackPackId={stackPackId}
                    fields={properties}
                  />
                );
              },
            );
          }

          return (
            <ConfigSection
              key={index}
              id={section.title}
              title={section.title}
              removable={false}
              defaultOpened={section.defaultOpened ?? true}
            >
              {[...section.propertyMap.entries()].map(
                ([stackPackId, properties], index) => {
                  if (properties.length === 0) {
                    return null;
                  }

                  return (
                    <ConfigGroup
                      key={index}
                      stackPackId={stackPackId}
                      fields={properties}
                    />
                  );
                },
              )}
            </ConfigSection>
          );
        })}
      </div>
    </ErrorBoundary>
  );
};
