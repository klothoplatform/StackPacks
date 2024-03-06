import type {
  ListProperty,
  MapProperty,
  NumberProperty,
  Property,
  SetProperty,
  StringProperty,
} from "../configuration-properties.ts";
import {
  CollectionTypes,
  PrimitiveTypes,
} from "../configuration-properties.ts";
import type { AppTemplate } from "./AppTemplate.ts";
import {
  resolveDefaultConfiguration,
  resolveAppTemplates,
} from "./AppTemplate.ts";

const mockStackPack: AppTemplate = {
  id: "base",
  alternatives: ["alternative1", "alternative2"],
  base: {},
  configuration: {},
  description: "This is a mock StackPack",
  name: "base",
  tags: ["tag1", "tag2"],
  version: "1.0.0",
};

describe("resolveDefaultConfiguration", () => {
  it("should resolve default configuration for a stack pack with various property types", () => {
    const inputStackPack: AppTemplate = {
      ...mockStackPack,
      id: "mockStackPack",
      name: "Mock Stack Pack",
      configuration: {
        stringProperty: {
          id: "stringProperty",
          name: "stringProperty",
          type: PrimitiveTypes.String,
          defaultValue: "defaultString",
        } as StringProperty,
        numberProperty: {
          id: "numberProperty",
          name: "numberProperty",
          type: PrimitiveTypes.Number,
          defaultValue: 0,
        } as NumberProperty,
        booleanProperty: {
          id: "booleanProperty",
          name: "booleanProperty",
          type: PrimitiveTypes.Boolean,
          defaultValue: false,
        } as Property,
        listProperty: {
          id: "listProperty",
          name: "listProperty",
          type: CollectionTypes.List,
          defaultValue: ["default1", "default2"],
          itemType: PrimitiveTypes.String,
        } as ListProperty,
        mapProperty: {
          id: "mapProperty",
          name: "mapProperty",
          type: CollectionTypes.Map,
          defaultValue: { key: "defaultKey", value: "defaultValue" },
          keyType: PrimitiveTypes.String,
          valueType: PrimitiveTypes.String,
        } as MapProperty,
        setProperty: {
          id: "setProperty",
          name: "setProperty",
          type: CollectionTypes.Set,
          defaultValue: ["default1", "default2"],
          itemType: PrimitiveTypes.String,
        } as SetProperty,
      },
    };

    const result = resolveDefaultConfiguration(inputStackPack);
    expect(result).toEqual({
      stringProperty: "defaultString",
      numberProperty: 0,
      booleanProperty: false,
      listProperty: ["default1", "default2"],
      mapProperty: { key: "defaultKey", value: "defaultValue" },
      setProperty: ["default1", "default2"],
    });
  });
});

describe("resolveStackPacks", () => {
  it("should resolve stack packs for valid IDs", () => {
    const stackPacks = new Map();
    stackPacks.set("mockStackPack", mockStackPack);

    const result = resolveAppTemplates(["mockStackPack"], stackPacks);
    expect(result).toEqual([mockStackPack]);
  });

  it("should resolve stack packs for invalid IDs", () => {
    const stackPacks = new Map();
    stackPacks.set("mockStackPack", mockStackPack);

    const result = resolveAppTemplates(["invalidID"], stackPacks);
    expect(result).toEqual([]);
  });

  it("should resolve stack packs for an empty array", () => {
    const stackPacks = new Map();
    stackPacks.set("mockStackPack", mockStackPack);

    const result = resolveAppTemplates([], stackPacks);
    expect(result).toEqual([]);
  });
});
