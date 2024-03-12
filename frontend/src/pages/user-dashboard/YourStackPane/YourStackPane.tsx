import type { FC } from "react";
import React, { useState } from "react";
import useApplicationStore from "../../store/ApplicationStore.ts";
import { UIError } from "../../../shared/errors.ts";
import { Badge, Button, Card, Dropdown, useThemeMode } from "flowbite-react";
import { useDocumentTitle } from "../../../hooks/useDocumentTitle.ts";
import { useNavigate } from "react-router-dom";
import {
  AiFillDelete,
  AiFillEye,
  AiOutlineCheckCircle,
  AiOutlineExclamationCircle,
  AiOutlineLoading3Quarters,
  AiOutlineQuestionCircle,
} from "react-icons/ai";
import classNames from "classnames";
import type { AppTemplate } from "../../../shared/models/AppTemplate.ts";
import { resolveAppTemplates } from "../../../shared/models/AppTemplate.ts";
import { BsThreeDotsVertical } from "react-icons/bs";
import { Tooltip } from "../../../components/Tooltip.tsx";
import { useClickedOutside } from "../../../hooks/useClickedOutside.ts";
import type { ApplicationDeployment } from "../../../shared/models/UserStack.ts";
import { toAppStatusString } from "../../../shared/models/UserStack.ts";
import { AppStatus } from "../../../shared/models/UserStack.ts";
import AWSLogoLight from "/images/Amazon_Web_Services_Logo.svg";
import AWSLogoDark from "/images/aws_logo_white.png";
import {
  outlineBadge,
  outlineOnlyBadge,
} from "../../../shared/custom-themes.ts";
import { RiUninstallFill } from "react-icons/ri";
import UninstallAppModal from "./UninstallAppModal.tsx";
import { ConfirmationModal } from "../../../components/ConfirmationModal.tsx";
import UninstallAllModal from "./UninstallAllModal.tsx";
import { HiMiniCog6Tooth } from "react-icons/hi2";
import { AppLogo } from "../../../components/AppLogo.tsx";

export const YourStackPane: FC = () => {
  const { userStack, addError, getUserStack, getStackPacks } =
    useApplicationStore();

  const { mode } = useThemeMode();
  const AWSLogo = mode === "dark" ? AWSLogoDark : AWSLogoLight;

  const navigate = useNavigate();

  const [stackPacks] = useState(new Map<string, AppTemplate>());

  useDocumentTitle("StackSnap - Your Stack");

  return (
    <div className="flex size-full flex-col gap-4 overflow-auto pr-4">
      <div className={"flex h-fit gap-1 py-1"}>
        <h2 className={"font-md text-xl"}>Your Stack</h2>
        <StackActions />
      </div>
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
        <div className={"flex w-full items-center justify-between"}>
          <h3 className={"font-md text-lg"}>Apps</h3>
          <Button
            size={"xs"}
            color={"purple"}
            onClick={() => navigate("./add-apps")}
          >
            <span>+</span>
          </Button>
        </div>
        {userStack && (
          <div className="flex size-full flex-col gap-4">
            {Object.entries(userStack.stack_packs).map(
              ([appTemplateId, appDeployment], index) => {
                const name =
                  resolveAppTemplates([appTemplateId], stackPacks)[0]?.name ??
                  appTemplateId;
                const status = appDeployment.status ?? AppStatus.Unknown;
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
  [AppStatus.Installing]: {
    color: "yellow",
    icon: () => <AiOutlineLoading3Quarters className="animate-spin" />,
    pulse: true,
  },
  [AppStatus.Installed]: {
    color: "green",
    icon: AiOutlineCheckCircle,
  },
  [AppStatus.InstallFailed]: {
    color: "red",
    icon: AiOutlineExclamationCircle,
  },
  [AppStatus.Updating]: {
    color: "green",
    icon: () => <AiOutlineLoading3Quarters className="animate-spin" />,
    pulse: true,
  },
  [AppStatus.UpdateFailed]: {
    color: "red",
    icon: AiOutlineExclamationCircle,
  },
  [AppStatus.Uninstalling]: {
    color: "yellow",
    icon: () => <AiOutlineLoading3Quarters className="animate-spin" />,
    pulse: true,
  },
  [AppStatus.UninstallFailed]: {
    color: "red",
    icon: AiOutlineExclamationCircle,
  },
  [AppStatus.Uninstalled]: {
    color: "green",
    icon: AiOutlineCheckCircle,
  },
  [AppStatus.Unknown]: {
    color: "gray",
    icon: AiOutlineQuestionCircle,
  },
  [AppStatus.New]: {
    color: "blue",
    icon: null,
  },
  default: {
    color: "gray",
    icon: null,
  },
};

const AppStatusBadge: FC<{ rtl?: boolean; status: AppStatus }> = ({
  rtl,
  status,
}) => {
  const navigate = useNavigate();
  const statusStyle = statusStyles[status] ?? statusStyles.default;
  const { mode } = useThemeMode();
  const theme = mode === "dark" ? outlineOnlyBadge : outlineBadge;
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
      onClick={() => navigate("./deployment-logs/latest")}
      className={classNames(
        "items-center flex w-fit flex-nowrap text-xs font-normal cursor-pointer",
        {
          "animate-pulse": (statusStyle as any).pulse,
        },
      )}
    >
      <span>{toAppStatusString(status)}</span>
    </Badge>
  );
};

const AppCard: FC<{ app: AppCardProps }> = ({ app }) => {
  const { mode } = useThemeMode();
  return (
    <Card className="flex h-fit w-full flex-col p-4">
      <div className="flex items-center justify-between gap-4 border-b border-gray-200 pb-2 dark:border-gray-700">
        <div className="flex items-center">
          <AppLogo
            className={"h-fit w-6"}
            appId={app.app_id.split("#")[1]}
            mode={mode}
          />
          <h4 className={"font-md ml-2 mr-4"}>{app.name}</h4>
          <AppStatusBadge status={app.status} rtl />
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
  const [showUninstallModal, setShowUninstallModal] = useState(false);
  const [showRemoveModal, setShowRemoveModal] = useState(false);
  const { updateStack, userStack, addError } = useApplicationStore();

  // handle tooltip visibility
  const [actionsTooltipDisabled, setActionsTooltipDisabled] = useState(true);
  const ref = React.useRef<HTMLDivElement>(null);
  useClickedOutside(ref, () => {
    setActionsTooltipDisabled(true);
  });

  const onRemoveApp = async () => {
    try {
      const updatedConfig = Object.fromEntries(
        Object.entries(userStack.stack_packs).map(([appId, app]) => [
          appId,
          app.configuration,
        ]),
      );
      delete updatedConfig[app.app_id.split("#")[1]];
      delete updatedConfig.common;
      await updateStack({
        configuration: updatedConfig,
      });
    } catch (e) {
      addError(
        new UIError({
          errorId: "OnRemoveApp",
          message: `Removing ${app.name} failed!`,
          cause: e,
        }),
      );
    }
  };

  return (
    <>
      <div className="flex w-fit items-center gap-1">
        <Tooltip content={"Modify Configuration"}>
          <Button
            color={mode}
            className={"size-fit"}
            size={"xs"}
            pill
            onClick={() => navigate(`./${app.app_id.split("#")[1]}/configure`)}
          >
            <HiMiniCog6Tooth />
          </Button>
        </Tooltip>
        <Tooltip
          disabled={!actionsTooltipDisabled}
          content={"Additional Actions"}
        >
          <Dropdown
            placement={"left-start"}
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
              {isInstalled(app) && (
                <Dropdown.Item
                  disabled={isBusy(app)}
                  icon={RiUninstallFill}
                  color={"red"}
                  onClick={() => setShowUninstallModal(true)}
                >{`Uninstall ${app.name}`}</Dropdown.Item>
              )}
              {!isInstalled(app) && !isBusy(app) && (
                <Dropdown.Item
                  icon={AiFillDelete}
                  color={"red"}
                  onClick={() => setShowRemoveModal(true)}
                >{`Remove ${app.name}`}</Dropdown.Item>
              )}
            </div>
          </Dropdown>
        </Tooltip>
      </div>
      {showUninstallModal && (
        <UninstallAppModal
          onClose={() => setShowUninstallModal(false)}
          id={app.app_id}
          name={app.name}
        />
      )}
      {showRemoveModal && (
        <ConfirmationModal
          cancelable
          title={`Remove "${app.name}"`}
          onClose={() => setShowRemoveModal(false)}
          confirmButtonLabel={"Remove"}
          prompt={`Are you sure you want to remove ${app.name} from your stack?`}
          confirmationText={"remove"}
          onConfirm={onRemoveApp}
        />
      )}
    </>
  );
};

const StackActions: FC = () => {
  const [showUninstallAllModal, setShowUninstallAllModal] = useState(false);

  return (
    <>
      <Dropdown
        theme={{
          floating: {
            base: "z-10 w-fit rounded divide-y divide-gray-100 shadow focus:outline-none -top-5",
          },
        }}
        className={"size-fit"}
        placement={"right-start"}
        label={<BsThreeDotsVertical />}
        arrowIcon={false}
        size={"xs"}
        inline
      >
        <Dropdown.Item
          icon={RiUninstallFill}
          onClick={() => setShowUninstallAllModal(true)}
        >
          Uninstall All Apps
        </Dropdown.Item>
      </Dropdown>
      {showUninstallAllModal && (
        <UninstallAllModal onClose={() => setShowUninstallAllModal(false)} />
      )}
    </>
  );
};

function isInstalled(app: ApplicationDeployment) {
  return [
    AppStatus.Installing,
    AppStatus.InstallFailed,
    AppStatus.UpdateFailed,
    AppStatus.Installed,
    AppStatus.UninstallFailed,
    AppStatus.Updating,
  ].includes(app.status);
}

function isBusy(app: ApplicationDeployment) {
  return [
    AppStatus.Installing,
    AppStatus.Uninstalling,
    AppStatus.Updating,
  ].includes(app.status);
}
