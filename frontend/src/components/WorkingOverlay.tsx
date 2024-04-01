import type { FC } from "react";
import React from "react";
import { Card, Spinner } from "flowbite-react";
import classNames from "classnames";

type WorkingOverlayProps = {
  show: boolean;
  message?: string;
  inset?: boolean;
  noOverlay?: boolean;
};
export const WorkingOverlay: FC<WorkingOverlayProps> = ({
  show,
  message,
  inset,
  noOverlay,
}) => {
  return (
    <div
      className={classNames(
        "flex flex-col items-center justify-center bg-gray-500/40 dark:bg-black/40",
        {
          "z-[1000]": !noOverlay,
          "fixed inset-0": inset,
          "size-full": !inset,
          hidden: !show,
        },
      )}
    >
      <Card className="flex flex-col justify-center p-8">
        {/* spinner doesn't seem to spin when toggling from the display without applying animate-spin to its parent */}
        <div className={"mx-auto animate-spin"}>
          <Spinner
            color={"purple"}
            className={"unset:animate-spin"} // prevents nested spinning animation
            size={"xl"}
          />
        </div>
        <div className="dark:text-gray-100">{message}</div>
      </Card>
    </div>
  );
};
