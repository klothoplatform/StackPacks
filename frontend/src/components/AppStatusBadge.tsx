import type { FC } from "react";
import React from "react";
import {
  AppLifecycleStatus,
  toAppStatusString,
} from "../shared/models/Project.ts";
import {
  AiOutlineCheckCircle,
  AiOutlineExclamationCircle,
  AiOutlineLoading3Quarters,
  AiOutlineQuestionCircle,
} from "react-icons/ai";
import { outlineBadge } from "../shared/custom-themes.ts";
import { Badge } from "flowbite-react";
import classNames from "classnames";

type AppStatusBadgeStyle = {
  color: string;
  icon?: FC;
  pulse?: boolean;
};
const statusStyles: Record<
  AppLifecycleStatus | "default",
  AppStatusBadgeStyle
> = {
  [AppLifecycleStatus.Installing]: {
    color: "yellow",
    icon: () => <AiOutlineLoading3Quarters className="animate-spin" />,
    pulse: true,
  },
  [AppLifecycleStatus.Installed]: {
    color: "green",
    icon: AiOutlineCheckCircle,
  },
  [AppLifecycleStatus.InstallFailed]: {
    color: "red",
    icon: AiOutlineExclamationCircle,
  },
  [AppLifecycleStatus.Updating]: {
    color: "green",
    icon: () => <AiOutlineLoading3Quarters className="animate-spin" />,
    pulse: true,
  },
  [AppLifecycleStatus.UpdateFailed]: {
    color: "red",
    icon: AiOutlineExclamationCircle,
  },
  [AppLifecycleStatus.Uninstalling]: {
    color: "yellow",
    icon: () => <AiOutlineLoading3Quarters className="animate-spin" />,
    pulse: true,
  },
  [AppLifecycleStatus.UninstallFailed]: {
    color: "red",
    icon: AiOutlineExclamationCircle,
  },
  [AppLifecycleStatus.Uninstalled]: {
    color: "gray",
  },
  [AppLifecycleStatus.Unknown]: {
    color: "gray",
    icon: AiOutlineQuestionCircle,
  },
  [AppLifecycleStatus.New]: {
    color: "blue",
  },
  [AppLifecycleStatus.Pending]: {
    color: "blue",
    pulse: true,
  },
  default: {
    color: "gray",
  },
};
export const AppStatusBadge: FC<{
  rtl?: boolean;
  status: AppLifecycleStatus;
}> = ({ rtl, status }) => {
  const statusStyle = statusStyles[status] ?? statusStyles.default;
  const theme = outlineBadge;
  return (
    <Badge
      size="xs"
      theme={{
        ...theme,
        icon: rtl
          ? {
              ...theme.icon,
              on: "rounded-md py-1 px-2 flex-row-reverse",
            }
          : {},
      }}
      icon={statusStyle.icon}
      color={statusStyle.color}
      className={classNames(
        "items-center flex w-fit flex-nowrap text-xs font-normal",
        {
          "animate-pulse": (statusStyle as any).pulse,
        },
      )}
    >
      <span>{toAppStatusString(status)}</span>
    </Badge>
  );
};
