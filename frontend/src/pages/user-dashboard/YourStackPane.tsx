import type { FC } from "react";
import { useState } from "react";
import React from "react";
import useApplicationStore from "../store/ApplicationStore.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { UIError } from "../../shared/errors.ts";
import { Badge, Button, Card, Dropdown, useThemeMode } from "flowbite-react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import { useNavigate } from "react-router-dom";
import {
  AiFillDelete,
  AiFillEye,
  AiFillTool,
  AiOutlineCheckCircle,
  AiOutlineExclamationCircle,
  AiOutlineLoading3Quarters,
  AiOutlineQuestionCircle,
} from "react-icons/ai";
import classNames from "classnames";
import type { AppTemplate } from "../../shared/models/AppTemplate.ts";
import { resolveAppTemplates } from "../../shared/models/AppTemplate.ts";
import { BsThreeDotsVertical } from "react-icons/bs";
import { Tooltip } from "../../components/Tooltip.tsx";
import { useClickedOutside } from "../../hooks/useClickedOutside.ts";
import type { ApplicationDeployment } from "../../shared/models/UserStack.ts";
import AWSLogoLight from "/images/Amazon_Web_Services_Logo.svg";
import AWSLogoDark from "/images/aws_logo_white.png";
import { outlineBadge } from "../../shared/custom-themes.ts";

export const YourStackPane: FC = () => {
  const { userStack, addError, getUserStack, getStackPacks } =
    useApplicationStore();

  const { mode } = useThemeMode();
  const AWSLogo = mode === "dark" ? AWSLogoDark : AWSLogoLight;

  const navigate = useNavigate();

  const [stackPacks, setStackPacks] = useState(new Map<string, AppTemplate>());

  useDocumentTitle("StackPacks - Your Stack");
  useEffectOnMount(() => {
    (async () => {
      try {
        const stack = await getUserStack();
        setStackPacks(await getStackPacks());
        if (!stack) {
          navigate("/onboarding");
        }
      } catch (e) {
        addError(
          new UIError({
            message: "Failed to load user stack",
            cause: e,
          }),
        );
      }
    })();
  });

  return (
    <div className="flex size-full flex-col gap-4 overflow-auto pr-4">
      <h2 className={"font-md text-xl"}>Your Stack</h2>
      <div className="flex flex-col gap-1">
        <h3 className={"font-md text-lg"}>Environment Details</h3>
        <Card className="flex h-fit w-full flex-col p-4">
          <ul className="flex flex-col text-sm">
            <li className={"flex h-fit items-center gap-1"}>
              <span>Provider:</span>
              <img className={"h-3"} src={AWSLogo} alt="AWS" />
            </li>
            <li>
              <span>Region: {userStack?.region}</span>
            </li>
          </ul>
        </Card>
      </div>
      <div className="flex flex-col gap-1">
        <h3 className={"font-md text-lg"}>Apps</h3>
        {userStack && (
          <div className="flex size-full flex-col gap-4">
            {Object.values(userStack.stack_packs).map(
              (appDeployment, index) => {
                const id =
                  appDeployment.app_id.split("#")[1] ?? appDeployment.app_id;
                const name =
                  resolveAppTemplates([id], stackPacks)[0]?.name ?? id;
                const status = appDeployment.status ?? "unknown";
                const app = { ...appDeployment, name, status };
                return <AppCard key={index} app={app} />;
              },
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const statusStyles = {
  installing: {
    color: "yellow",
    icon: () => <AiOutlineLoading3Quarters className="animate-spin" />,
    pulse: true,
  },
  installed: {
    color: "green",
    icon: AiOutlineCheckCircle,
  },
  failed: {
    color: "red",
    icon: AiOutlineExclamationCircle,
  },
  unknown: {
    color: "gray",
    icon: AiOutlineQuestionCircle,
  },
  default: {
    color: "gray",
    icon: null,
  },
};

const AppStatusBadge: FC<{ rtl?: boolean; status: string }> = ({
  rtl,
  status,
}) => {
  const navigate = useNavigate();
  const statusStyle = statusStyles[status] ?? statusStyles.default;
  return (
    <Badge
      size="xs"
      theme={{
        ...outlineBadge,
        icon: rtl
          ? {
              ...outlineBadge.icon,
              on: "rounded-md py-1 px-2 flex-row-reverse",
            }
          : {},
      }}
      icon={statusStyle.icon}
      color={statusStyle.color}
      onClick={() => navigate("./deployment-logs/latest")}
      className={classNames(
        "items-center flex w-fit flex-nowrap text-xs font-normal cursor-pointer",
        {
          "animate-pulse": statusStyle.pulse,
        },
      )}
    >
      <span>{status}</span>
    </Badge>
  );
};

const AppCard: FC<{ app: AppCardProps }> = ({ app }) => {
  return (
    <Card className="flex h-fit w-full flex-col p-4">
      <div className="flex items-center justify-between gap-4 border-b border-gray-200 pb-2 dark:border-gray-700">
        <div className="flex items-center gap-4 px-2">
          <h4 className={"font-md"}>{app.name}</h4>
          <Tooltip disabled={!app.status_reason} content={app.status_reason}>
            <AppStatusBadge status={app.status} rtl />
          </Tooltip>
        </div>
        <AppButtonGroup {...app} />
      </div>
      <h5 className={"font-md text-md"}>Configuration</h5>
      <ul className="flex flex-col text-xs">
        {Object.entries(app.configuration).map(([key, value], index) => {
          return (
            <li key={index}>
              <span>
                {key}: {value}
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
};

interface AppCardProps extends ApplicationDeployment {
  name: string;
}

const AppButtonGroup: FC<AppCardProps> = (app) => {
  const { mode } = useThemeMode();
  const navigate = useNavigate();

  // handle tooltip visibility
  const [actionsTooltipDisabled, setActionsTooltipDisabled] = useState(true);
  const ref = React.useRef<HTMLDivElement>(null);
  useClickedOutside(ref, () => {
    setActionsTooltipDisabled(true);
  });

  return (
    <div className="flex w-fit items-center gap-1">
      <Tooltip content={"Modify Configuration"}>
        <Button color={mode} className={"size-fit"} size={"xs"} pill>
          <AiFillTool />
        </Button>
      </Tooltip>
      <Tooltip
        disabled={!actionsTooltipDisabled}
        content={"Additional Actions"}
      >
        <Dropdown
          placement={"bottom-start"}
          label={<BsThreeDotsVertical />}
          arrowIcon={false}
          size={"xs"}
          color={""}
        >
          {/* eslint-disable-next-line jsx-a11y/mouse-events-have-key-events */}
          <div onMouseOver={() => setActionsTooltipDisabled(false)} ref={ref}>
            <Dropdown.Item
              icon={AiFillEye}
              onClick={() => {
                navigate("./deployment-logs");
              }}
            >
              View Logs
            </Dropdown.Item>
            <Dropdown.Item
              icon={AiFillDelete}
              color={"red"}
            >{`Uninstall ${app.name}`}</Dropdown.Item>
          </div>
        </Dropdown>
      </Tooltip>
    </div>
  );
};
