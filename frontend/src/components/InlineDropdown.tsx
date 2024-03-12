import type { FC, PropsWithChildren } from "react";
import type { DropdownProps, FlowbiteColors } from "flowbite-react";
import { Dropdown } from "flowbite-react";

const prefixColors: Record<keyof FlowbiteColors, string> = {
  light: "text-gray-500 dark:text-gray-300",
  dark: "text-gray-300 dark:text-gray-500",
  gray: "text-gray-500 dark:text-gray-300",
  blue: "text-blue-300 dark:text-blue-300",
  green: "text-green-500 dark:text-green-300",
  red: "text-red-300 dark:text-red-300",
  yellow: "text-yellow-500 dark:text-yellow-300",
  indigo: "text-indigo-500 dark:text-indigo-300",
  purple: "text-purple-500 dark:text-purple-300",
  pink: "text-pink-500 dark:text-pink-300",
  teal: "text-teal-500 dark:text-teal-300",
  cyan: "text-cyan-500 dark:text-cyan-300",
  lime: "text-lime-500 dark:text-lime-300",
  success: "text-green-300 dark:text-green-300",
  failure: "text-red-300 dark:text-red-300",
  info: "text-blue-300 dark:text-blue-300",
  warning: "text-yellow-300 dark:text-yellow-300",
};

export const InlineDropdown: FC<
  PropsWithChildren<
    {
      prefix: string;
      label: string;
    } & DropdownProps
  >
> = ({ prefix, label, children, ...rest }) => {
  const color = rest.color ?? "blue";

  return (
    <Dropdown
      label={
        <div>
          <span className={`${prefixColors[color]}`}>{prefix}: </span>
          {label}
        </div>
      }
      placement={"bottom-start"}
      {...rest}
    >
      {children}
    </Dropdown>
  );
};
