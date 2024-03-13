import Gitea from "/images/logos/gitea.svg";
import Mattermost from "/images/logos/mattermost.svg";
import mattermostDark from "/images/logos/mattermost-dark.svg";
import Gitness from "/images/logos/gitness.svg";
import GitnessDark from "/images/logos/gitness-dark.svg";
import ToolJet from "/images/logos/tooljet.svg";
import type { FC, ImgHTMLAttributes } from "react";
import { twMerge } from "tw-merge";
import Metabase from "/images/logos/metabase.svg";
import Strapi from "/images/logos/strapi.svg";
import Supertokens from "/images/logos/supertokens.svg";
import SupertokensDark from "/images/logos/supertokens-dark.svg";
import Typesense from "/images/logos/typesense.png";

export interface LogoMapping {
  filePath: string;
  darkPath?: string;
  className?: string;
}

const LogoMappings: Record<string, string | LogoMapping> = {
  Gitea,
  Gitness: {
    filePath: Gitness,
    darkPath: GitnessDark,
    className: "h-8",
  },
  Mattermost: {
    filePath: Mattermost,
    darkPath: mattermostDark,
  },
  ToolJet,
  Metabase,
  Strapi,
  Supertokens: {
    filePath: Supertokens,
    darkPath: SupertokensDark,
  },
  Typesense,
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
