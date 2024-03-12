import type { FC } from "react";
import { useEffect } from "react";
import React, { createContext } from "react";
import { useState } from "react";
import type {
  CardProps,
  CustomFlowbiteTheme,
  FlowbiteColors,
} from "flowbite-react";
import { Card } from "flowbite-react";
import { twMerge } from "tw-merge";

type SelectableCardProps = CardProps & {
  selected?: boolean;
  onSelect?: () => void;
  onDeselect?: () => void;
  outline?: boolean;
  color?: keyof FlowbiteColors | "primary";
};

const outlineStyles = {
  light: "border border-primary-300 dark:border-primary-500",
  dark: "border border-primary-500 dark:border-primary-300",
  blue: "border border-blue-300 dark:border-blue-500",
  purple: "border border-purple-300 dark:border-purple-500",
  primary: "border border-primary-300 dark:border-primary-500",
  green: "border border-green-300 dark:border-green-500",
  red: "border border-red-300 dark:border-red-500",
  yellow: "border border-yellow-300 dark:border-yellow-500",
  success: "border border-success-300 dark:border-success-500",
  warning: "border border-warning-300 dark:border-warning-500",
  info: "border border-info-300 dark:border-info-500",
  failure: "border border-failure-300 dark:border-failure-500",
};

const normalStyles = {
  light:
    "border border-primary-300 dark:border-primary-500 bg-primary-300 dark:bg-primary-700",
  dark: "border border-primary-500 dark:border-primary-300 bg-primary-700 dark:bg-primary-300",
  blue: "border border-blue-300 dark:border-blue-500 bg-blue-300 dark:bg-blue-700",
  purple:
    "border border-purple-300 dark:border-purple-500 bg-purple-300 dark:bg-purple-700",
  primary:
    "border border-primary-300 dark:border-primary-500 bg-primary-300 dark:bg-primary-700",
  green:
    "border border-green-300 dark:border-green-500 bg-green-300 dark:bg-green-700",
  red: "border border-red-300 dark:border-red-500 bg-red-300 dark:bg-red-700",
  yellow:
    "border border-yellow-300 dark:border-yellow-500 bg-yellow-300 dark:bg-yellow-700",
  success:
    "border border-success-300 dark:border-success-500 bg-success-300 dark:bg-success-700",
  warning:
    "border border-warning-300 dark:border-warning-500 bg-warning-300 dark:bg-warning-700",
  info: "border border-info-300 dark:border-info-500 bg-info-300 dark:bg-info-700",
  failure:
    "border border-failure-300 dark:border-failure-500 bg-failure-300 dark:bg-failure-700",
};

const selectedTheme: (
  color: keyof FlowbiteColors | "primary",
  outline?: boolean,
) => CustomFlowbiteTheme["card"] = (color, outline) => {
  const colorStyles = outline ? outlineStyles : normalStyles;
  return {
    root: {
      base: twMerge(`"flex rounded-lg ${colorStyles[color]}`),
      children: "flex h-full flex-col justify-center gap-4",
      horizontal: {
        off: "flex-col",
        on: "flex-col md:max-w-xl md:flex-row",
      },
      href: "hover:bg-gray-100 dark:hover:bg-gray-700",
    },
  };
};

export const SelectableCard: FC<SelectableCardProps> = ({
  selected,
  onSelect,
  onDeselect,
  outline,
  color,
  children,
  className,
  ...props
}) => {
  color = color || "primary";
  const [isSelected, setIsSelected] = useState(selected);

  useEffect(() => {
    setIsSelected(selected);
  }, [selected]);

  const onClick = (shouldSelect: boolean) => {
    if (shouldSelect) {
      setIsSelected(true);
      onSelect?.();
    } else {
      setIsSelected(false);
      onDeselect?.();
    }
  };

  return (
    <SelectableCardContext.Provider
      value={{ selected: isSelected, setSelected: setIsSelected }}
    >
      <Card
        {...props}
        className={twMerge(`cursor-pointer ${className}`)}
        theme={isSelected ? selectedTheme(color, outline) : undefined}
        onClick={() => onClick(!isSelected)}
      >
        {children}
      </Card>
    </SelectableCardContext.Provider>
  );
};

interface CardContextProps {
  selected: boolean;
  setSelected: (selected: boolean) => void;
}

const SelectableCardContext = createContext<CardContextProps>({
  selected: false,
  setSelected: () => {},
});
