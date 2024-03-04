import type { Property } from "../configuration-properties.ts";

export interface StackPack {
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

export function resolveStackPacks(
  ids: string[],
  stackPacks: Map<string, StackPack>,
): StackPack[] {
  const packs = ids.map((id) => stackPacks.get(id)).filter((pack) => pack);
  return packs;
}
