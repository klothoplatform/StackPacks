import Gitea from "/images/logos/gitea.svg";
import Mattermost from "/images/logos/mattermost.svg";
import mattermostDark from "/images/logos/mattermost-dark.svg";
import Gitness from "/images/logos/gitness.svg";
import GitnessDark from "/images/logos/gitness-dark.svg";
import ToolJet from "/images/logos/tooljet.svg";
import Metabase from "/images/logos/metabase.svg";
import Strapi from "/images/logos/strapi.svg";
import SuperTokens from "/images/logos/supertokens.svg";
import SuperTokensDark from "/images/logos/supertokens-dark.svg";
import CalCom from "/images/logos/cal-com.svg";
import Keila from "/images/logos/keila.svg";
import Matomo from "/images/logos/matomo.svg";
import OwnCloud from "/images/logos/owncloud.svg";
import Rallly from "/images/logos/rallly.svg";
import TypeSense from "/images/logos/typesense.png";

export interface LogoMapping {
  filePath: string;
  darkPath?: string;
  className?: string;
}

export const LogoMappings: Record<string, string | LogoMapping> = {
  calcom: CalCom,
  gitea: Gitea,
  gitness: {
    filePath: Gitness,
    darkPath: GitnessDark,
    className: "h-8",
  },
  keila: Keila,
  matomo: Matomo,
  owncloud: OwnCloud,
  mattermost: {
    filePath: Mattermost,
    darkPath: mattermostDark,
  },
  tooljet: ToolJet,
  metabase: Metabase,
  rallly: Rallly,
  strapi: Strapi,
  supertokens: {
    filePath: SuperTokens,
    darkPath: SuperTokensDark,
  },
  typesense: TypeSense,
};

export function hasMapping(appId: string) {
  return !!LogoMappings[appId];
}
