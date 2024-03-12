import gitea from "/images/logos/gitea.svg";
import mattermost from "/images/logos/mattermost.svg";
import mattermostWhite from "/images/logos/mattermost-white.svg";
import gitness from "/images/logos/gitness.svg";
import gitnessWhite from "/images/logos/gitness-white.svg";
import tooljet from "/images/logos/tooljet.svg";
import type { FC, ImgHTMLAttributes } from "react";
import { twMerge } from "tw-merge";

export interface LogoMapping {
  filePath: string;
  darkPath?: string;
  className?: string;
}

const LogoMappings: Record<string, string | LogoMapping> = {
  gitea,
  gitness: {
    filePath: gitness,
    darkPath: gitnessWhite,
    className: "h-8",
  },
  mattermost: {
    filePath: mattermost,
    darkPath: mattermostWhite,
  },
  tooljet,
};

export const AppLogo: FC<
  ImgHTMLAttributes<any> & { appId: string; mode?: string }
> = ({ appId, mode, className, ...rest }) => {
  let mapping = LogoMappings[appId];
  if (!mapping) {
    return null;
  }
  if (typeof mapping === "string") {
    mapping = { filePath: mapping, darkPath: mapping };
  }
  className = twMerge(
    "h-10" +
      (className ? ` ${className}` : "") +
      (mapping.className ? ` ${mapping.className}` : ""),
  );

  return (
    <img
      src={
        mode === "dark"
          ? mapping.darkPath ?? mapping.filePath
          : mapping.filePath
      }
      alt={appId}
      className={className}
      {...rest}
    />
  );
};
