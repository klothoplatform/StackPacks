import type { FC, PropsWithChildren } from "react";

export const InstructionalStep: FC<
  PropsWithChildren<{
    title: string;
    optional?: boolean;
  }>
> = ({ title, optional, children }) => {
  return (
    <div className={"flex h-fit w-full flex-col gap-2"}>
      <h3
        className={"text-lg font-medium text-primary-500 dark:text-primary-400"}
      >
        {title}
        {optional && (
          <span className={"text-sm text-gray-500 dark:text-gray-400"}>
            {" (optional)"}
          </span>
        )}
      </h3>
      {children}
    </div>
  );
};
