import gitea from "/images/logos/gitea.svg";
import mattermost from "/images/logos/mattermost.svg";
import mattermostDark from "/images/logos/mattermost-dark.svg";
import gitness from "/images/logos/gitness.svg";
import gitnessDark from "/images/logos/gitness-dark.svg";
import tooljet from "/images/logos/tooljet.svg";
import type { FC, ImgHTMLAttributes } from "react";
import { twMerge } from "tw-merge";
import metabase from "/images/logos/metabase.svg";
import strapi from "/images/logos/strapi.svg";
import supertokens from "/images/logos/supertokens.svg";
import supertokensDark from "/images/logos/supertokens-dark.svg";
import typesense from "/images/logos/typesense.png";

export interface LogoMapping {
  filePath: string;
  darkPath?: string;
  className?: string;
}

const LogoMappings: Record<string, string | LogoMapping> = {
  gitea,
  gitness: {
    filePath: gitness,
    darkPath: gitnessDark,
    className: "h-8",
  },
  mattermost: {
    filePath: mattermost,
    darkPath: mattermostDark,
  },
  tooljet,
  metabase,
  strapi,
  supertokens: {
    filePath: supertokens,
    darkPath: supertokensDark,
  },
  typesense,
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
