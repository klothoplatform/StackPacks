/*
 * stackPacks: {name -> user_confg_map} dict[str <name of stack pack>, dict[str <config keys from the stackpack.configuration>, Any]]
 * eg: {"mattermost": {"Cpu": 1024, "DBPassword": "hunter2"}}
 * note: versioning TBD, solve later [maybe {"mattermost": {"__version": 2}} ?]
 * region
 * aws iam role
 * arn
 * external id
 * deploymentStatus
 * deploymentStatusReason
 * owner
 * creationTime
 */

import type { StackPack } from "./StackPack.ts";
import { resolveDefaultConfiguration, resolveStackPacks } from "./StackPack.ts";
import type { Property } from "../configuration-properties.ts";
import {
  CollectionTypes,
  type ListProperty,
  type MapProperty,
} from "../configuration-properties.ts";
import { isCollection } from "yaml";

export interface Stack {
  assumed_role_arn: string;
  assumed_role_external_id: string;
  created_at: number;
  created_by: string;
  status: "new" | "not-started" | "running" | "succeeded" | "failed";
  statusReason: string;
  id: string;
  name: string;
  owner: string;
  configuration: Configuration;
  region: string;
}

export interface Configuration {
  //stack pack name
  [key: string]: {
    // config key (e.g. CPU)
    [key: string]: any;
  };
}

export function resolveDefaultConfigurations(
  stack: Stack,
  stackPacks: Map<string, StackPack>,
): Configuration {
  const configuration: Configuration = {};
  const packs = resolveStackPacks(
    Object.keys(stack.configuration ?? {}),
    stackPacks,
  );
  packs.forEach((pack) => {
    configuration[pack.id] = resolveDefaultConfiguration(pack);
  });
  return configuration;
}

export function toFormState(
  stackPackConfig: { [key: string]: any },
  fields: Property[] = [],
  stackPackId?: string,
) {
  const formState: any = {};
  if (!stackPackConfig) {
    return formState;
  }

  const props = new Set([
    ...Object.keys(stackPackConfig),
    ...fields.map((f) => f.id),
  ]);

  props.forEach((property) => {
    let key = property;
    if (stackPackId) {
      key = `${stackPackId}#${property}`;
    }

    const value = stackPackConfig[property];
    const field = fields.find((field) => field.id === property);
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

export function resolveConfigFromFormState(
  formState: any,
  fields: Property[] = [],
): { [key: string]: any } {
  if (!formState) {
    return {};
  }

  const config: Configuration = {};

  fields = fields.filter(
    (field) =>
      !field.deployTime && !field.configurationDisabled && !field.synthetic,
  );

  Object.keys(formState).forEach((configKey) => {
    if (!configKey) {
      return {};
    }
    const value = formState[configKey];
    const field = fields.find((field) => field.id === configKey);
    if (!field) {
      return {};
    }
    switch (field?.type) {
      case CollectionTypes.Map:
        if (isCollection((field as MapProperty).valueType)) {
          setConfigEntry({
            config,
            configKey,
            value: resolveConfigFromFormState(value, field.properties),
          });
        } else {
          setConfigEntry({
            config,
            configKey,
            value: Object.fromEntries(
              value.map((item: any) => {
                return [item.key, item.value];
              }),
            ),
          });
        }
        break;
      case CollectionTypes.Set:
      case CollectionTypes.List:
        setConfigEntry({
          config,
          configKey,
          value: value.map((item: any) => {
            if (isCollection((field as ListProperty).itemType)) {
              return resolveConfigFromFormState(item, field.properties);
            }
            return item.value;
          }),
        });
        break;
      default:
        setConfigEntry({
          config,
          configKey,
          value,
        });
    }
  });
  return config;
}

interface ConfigEntry {
  config: Configuration;
  configKey: string;
  value: any;
}
function setConfigEntry(entry: ConfigEntry) {
  const { config, configKey, value } = entry;
  let current = config as any;
  const pathParts = configKey.split(".");
  const last = pathParts.pop();
  pathParts.forEach((part) => {
    const isArrayIndex = /^\[\d+]$/.test(part);
    if (isArrayIndex) {
      const index = parseInt(part.replaceAll(/^[[\]]/, ""), 10);
      if (!Array.isArray(current)) {
        current = [];
      }
      if (current[index] === undefined) {
        current[index] = {};
      }
      current = current[index];
    } else {
      if (!current[part]) {
        current[part] = {};
      }
      current = current[part];
    }
  });
  if (/^\[\d+]$/.test(last)) {
    const index = parseInt(last.replaceAll(/^[[\]]/, ""), 10);
    if (!Array.isArray(current)) {
      current = [];
    }
    current[index] = value;
  } else {
    current[last] = value;
  }
}
