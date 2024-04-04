import type { FC, HTMLAttributes } from "react";
import React from "react";
import { twMerge } from "tailwind-merge";

export interface ContainerProps extends HTMLAttributes<HTMLDivElement> {}

export const Container: FC<ContainerProps> = ({
  children,
  className,
  ...rest
}) => {
  return (
    <div
      className={twMerge(
        "h-fit w-full flex flex-col gap-2 rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
};

export interface ContainerHeaderProps
  extends HTMLAttributes<HTMLHeadingElement> {
  border?: boolean;
  size?: "sm" | "md" | "lg" | "xl";
}

export const ContainerHeader: FC<ContainerHeaderProps> = ({
  border,
  size,
  children,
  className,
  ...rest
}) => {
  size = size ?? "md";

  return (
    <h2
      className={twMerge(
        "flex gap-10 dark:text-white font-bold",
        border && "border-b border-gray-200 dark:border-gray-700",
        size === "sm" && "text-md",
        size === "md" && "text-lg",
        size === "lg" && "text-xl",
        size === "xl" && "text-2xl",
        className,
      )}
      {...rest}
    >
      {children}
    </h2>
  );
};
