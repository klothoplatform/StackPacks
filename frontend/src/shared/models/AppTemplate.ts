import type { Property } from "../configuration-properties.ts";
import { getNewConfiguration } from "../configuration-properties.ts";

export interface AppTemplate {
  id: string;
  alternatives: string[];
  configuration: {
    [key: string]: Property;
  };
  base: any;
  description: string;
  name: string;
  tags: string[];
  version: string;
}

export function resolveAppTemplates(
  ids: string[],
  stackPacks: Map<string, AppTemplate>,
): AppTemplate[] {
  return ids.map((id) => stackPacks.get(id)).filter((pack) => pack);
}

export function resolveDefaultConfiguration(pack: AppTemplate): object {
  if (!(Object.keys(pack.configuration ?? {}).length > 0)) {
    return {};
  }
  let configuration = getNewConfiguration(Object.values(pack.configuration));
  Object.entries(pack.configuration).forEach(([key, property]) => {
    configuration[key] = property.defaultValue ?? configuration[key];
  });
  return configuration;
}
