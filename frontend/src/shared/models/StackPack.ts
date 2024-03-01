import type { Property } from "../configuration-properties.ts";

export interface StackPack {
  alternatives: string[];
  configuration: {
    [key: string]: Property;
  };
  description: string;
  name: string;
  tags: string[];
  version: string;
}
