export function isObject(value: any): boolean {
  return typeof value === "object" && !Array.isArray(value) && value !== null;
}

export function getEnumKeyByEnumValue<
  T extends {
    [index: string]: string;
  },
>(myEnum: T, enumValue: string): keyof T | null {
  let keys = Object.keys(myEnum).filter((x) => myEnum[x] === enumValue);
  return keys.length > 0 ? keys[0] : null;
}

export function qualifiedProperties(obj: any): string[] {
  const properties: string[] = [];
  if (!isObject(obj) && !Array.isArray(obj)) {
    return properties;
  }
  if (Array.isArray(obj)) {
    for (const [index, value] of obj.entries()) {
      const childProperties = qualifiedProperties(value);
      properties.push(`[${index}]`);
      properties.push(
        ...childProperties.map(
          (childProperty) =>
            `[${index}]${
              childProperty.startsWith("[") ? "" : "."
            }${childProperty}`,
        ),
      );
    }
  } else {
    for (const property of Object.keys(obj)) {
      properties.push(property);
      const child = obj[property];
      if (isObject(child) || Array.isArray(child)) {
        const childProperties = qualifiedProperties(child);
        properties.push(
          ...childProperties.map(
            (childProperty) =>
              `${property}${
                childProperty.startsWith("[") ? "" : "."
              }${childProperty}`,
          ),
        );
      }
    }
  }
  return properties;
}

export function propertyDepth(property: string): number {
  return property.split(/[.[]/).length - 1;
}

export function getModifiedFields(
  original: any,
  submitted: any,
  dirty: any,
): string[] {
  const properties: string[] = [];
  if (!isObject(original) && !Array.isArray(original)) {
    return properties;
  }
  if (Array.isArray(original)) {
    for (const [index, value] of original.entries()) {
      const childProperties = getModifiedFields(
        value,
        submitted[index],
        dirty[index],
      );
      if (dirty[index]) {
        properties.push(`[${index}]`);
        properties.push(
          ...childProperties.map(
            (childProperty) =>
              `[${index}]${
                childProperty.startsWith("[") ? "" : "."
              }${childProperty}`,
          ),
        );
      }
    }
  } else {
    for (const property of Object.keys(original)) {
      const child = original[property];
      if (isObject(child) || Array.isArray(child)) {
        const childProperties = getModifiedFields(
          child,
          submitted[property],
          dirty[property],
        );
        if (dirty[property]) {
          properties.push(
            ...childProperties.map(
              (childProperty) =>
                `${property}${
                  childProperty.startsWith("[") ? "" : "."
                }${childProperty}`,
            ),
          );
        }
      } else if (dirty[property]) {
        properties.push(property);
      }
    }
  }
  return properties;
}

export function arrayEquals<T>(
  a: T[] | undefined,
  b: T[] | undefined,
): boolean {
  if (a === b) {
    return true;
  }
  if (a === undefined || b === undefined) {
    return false;
  }
  return (
    Array.isArray(a) &&
    Array.isArray(b) &&
    a.length === b.length &&
    a.every((val, index) => val === b[index])
  );
}

export function setEquals<T>(
  a: Set<T> | undefined,
  b: Set<T> | undefined,
): boolean {
  if (a === b) {
    return true;
  }
  if (a === undefined || b === undefined) {
    return false;
  }

  return a.size === b.size && [...a].every((value) => b.has(value));
}

// findChildProperty finds a child property of an object by path.
// A period indicates a child property, a "[]" indicates an array index.
export function findChildProperty(obj: any, path: string): any {
  const parts = path.split(/[[.]/);
  let current: any = obj;
  for (const part of parts) {
    if (current === undefined) {
      return undefined;
    }
    if (part.endsWith("]")) {
      const index = parseInt(
        part.substring(part.indexOf("[") + 1, part.length),
        10,
      );
      current = current[index];
    } else {
      current = current[part];
    }
  }
  return current;
}
