import type { FC } from "react";
import type { TooltipProps } from "flowbite-react";
import { Tooltip as FBTooltip } from "flowbite-react";

export const Tooltip: FC<TooltipProps & { disabled?: boolean }> = ({
  disabled,
  ...props
}) => {
  return (
    <FBTooltip className={disabled ? "hidden" : ""} {...props}>
      {props.children}
    </FBTooltip>
  );
};
