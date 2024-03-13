import type { FC } from "react";
import { useEffect } from "react";
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
import { resolveAppTemplates } from "../../../shared/models/AppTemplate.ts";
import { BsThreeDotsVertical } from "react-icons/bs";
import { Tooltip } from "../../../components/Tooltip.tsx";
import { useClickedOutside } from "../../../hooks/useClickedOutside.ts";
import type {
  ApplicationDeployment,
  AppStatus,
} from "../../../shared/models/UserStack.ts";
import {
  AppDeploymentStatus,
  AppLifecycleStatus,
  hasDeploymentInProgress,
  toAppStatusString,
} from "../../../shared/models/UserStack.ts";
import AWSLogoLight from "/images/Amazon_Web_Services_Logo.svg";
import AWSLogoDark from "/images/aws_logo_white.png";
import {
  outlineBadge,
  outlineOnlyBadge,
} from "../../../shared/custom-themes.ts";
import { RiInstallFill, RiUninstallFill } from "react-icons/ri";
import UninstallAppModal from "./UninstallAppModal.tsx";
import { ConfirmationModal } from "../../../components/ConfirmationModal.tsx";
import UninstallAllModal from "./UninstallAllModal.tsx";
import { HiMiniCog6Tooth } from "react-icons/hi2";
import { AppLogo } from "../../../components/AppLogo.tsx";
import { useInterval } from "usehooks-ts";
import { CollapsibleSection } from "../../../components/CollapsibleSection.tsx";
import { IoRefresh } from "react-icons/io5";
import { SlRefresh } from "react-icons/sl";

export const YourStackPane: FC = () => {
  const { userStack, getUserStack, userStackPolicy, stackPacks } =
    useApplicationStore();

  const [isRefreshing, setIsRefreshing] = useState(false);

  const { mode } = useThemeMode();
  const AWSLogo = mode === "dark" ? AWSLogoDark : AWSLogoLight;
  const navigate = useNavigate();
  const [refreshInterval, setRefreshInterval] = useState(30 * 1000);

  useDocumentTitle("StackSnap - Your Stack");

  useEffect(() => {
    if (hasDeploymentInProgress(userStack)) {
      setRefreshInterval(8 * 1000);
    } else {
      setRefreshInterval(30 * 1000);
    }
  }, [userStack]);

  useInterval(async () => {
    if (hasDeploymentInProgress(userStack)) {
      setIsRefreshing(true);
      try {
        await getUserStack(true);
      } finally {
        setIsRefreshing(false);
      }
    }
  }, refreshInterval);

  const onRefresh = async () => {
    setIsRefreshing(true);
    try {
      await getUserStack(true);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="flex size-full flex-col gap-4 overflow-y-auto pr-4">
      <div className={"flex size-full justify-between py-1"}>
        <div className={"flex h-fit gap-1"}>
          <h2 className={"font-md text-xl"}>Your Stack</h2>
          <StackActions />
        </div>
        <Button
          title={"Refresh Stack"}
          size={"xs"}
          color={mode}
          disabled={isRefreshing}
          outline
          onClick={onRefresh}
        >
          <SlRefresh
            className={classNames({
              "animate-spin": isRefreshing,
            })}
          />
        </Button>
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
            <li>
              <span>Deployment Role ARN: {userStack?.assumed_role_arn}</span>
            </li>
            <li>
              <CollapsibleSection
                size={"xs"}
                collapsedText={"Show deployment policy"}
                collapsed
                expandedText={"Hide"}
                color={mode}
              >
                <Card
                  className={
                    "max-h-80 overflow-auto whitespace-pre-wrap p-2 font-mono text-xs dark:text-gray-200"
                  }
                >
                  {userStack?.policy || userStackPolicy}
                </Card>
              </CollapsibleSection>
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
                const status =
                  appDeployment.status ?? AppLifecycleStatus.Uninstalled;
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

type AppStatusBadgeStyle = {
  color: string;
  icon?: FC;
  pulse?: boolean;
};

const statusStyles: Record<keyof AppStatus | "default", AppStatusBadgeStyle> = {
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
  [AppDeploymentStatus.Failed]: {
    color: "red",
    icon: AiOutlineExclamationCircle,
  },
  [AppDeploymentStatus.InProgress]: {
    color: "yellow",
    icon: () => <AiOutlineLoading3Quarters className="animate-spin" />,
    pulse: true,
  },
  [AppDeploymentStatus.Succeeded]: {
    color: "green",
    icon: AiOutlineCheckCircle,
  },
  default: {
    color: "gray",
  },
};

const AppStatusBadge: FC<{ rtl?: boolean; status: AppLifecycleStatus }> = ({
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
      {!!app.status_reason && (
        <CollapsibleSection
          size={"xs"}
          collapsedText={"Show reason"}
          expandedText={"Hide reason"}
          color={app.status === AppDeploymentStatus.Failed ? "red" : mode}
        >
          <Card className="flex max-h-80 flex-col gap-2 overflow-auto whitespace-pre-wrap p-2">
            <div
              className={"size-full py-2 font-mono text-xs dark:text-gray-200"}
            >
              {app.status_reason}
            </div>
          </Card>
        </CollapsibleSection>
      )}
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
  const { removeApp, addError, installApp } = useApplicationStore();

  // handle tooltip visibility
  const [actionsTooltipDisabled, setActionsTooltipDisabled] = useState(true);
  const ref = React.useRef<HTMLDivElement>(null);
  useClickedOutside(ref, () => {
    setActionsTooltipDisabled(true);
  });

  const onRemoveApp = async () => {
    try {
      await removeApp(app.app_id.split("#")[1]);
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

  const [deployId, setDeployId] = useState<string | null>(null);

  const onInstallApp = async () => {
    try {
      const deployId = await installApp(app.app_id.split("#")[1]);
      setDeployId(deployId);
    } catch (e) {
      addError(
        new UIError({
          errorId: "OnInstallApp",
          message: `Installing ${app.name} failed!`,
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
                  if (deployId) {
                    navigate(`/user/dashboard/deploy/${deployId}`);
                  } else {
                    navigate(`/user/dashboard/deploy/latest`);
                  }
                }}
              >
                View Logs
              </Dropdown.Item>
              <Dropdown.Divider />
              {!isInstalled(app) && !isBusy(app) && (
                <Dropdown.Item
                  disabled={isBusy(app)}
                  icon={RiInstallFill}
                  onClick={onInstallApp}
                >
                  Install {app.name}
                </Dropdown.Item>
              )}
              {isInstalled(app) && (
                <Dropdown.Item
                  disabled={isBusy(app)}
                  icon={IoRefresh}
                  onClick={() => onInstallApp()}
                >
                  Redeploy {app.name}
                </Dropdown.Item>
              )}
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
          id={app.app_id.split("#")[1]}
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
  const { installStack, userStack } = useApplicationStore();
  const [showUninstallAllModal, setShowUninstallAllModal] = useState(false);

  const canTriggerStackAction =
    userStack && !hasDeploymentInProgress(userStack);

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
          disabled={!canTriggerStackAction}
          icon={IoRefresh}
          onClick={async () => await installStack()}
        >
          Redeploy All Apps
        </Dropdown.Item>
        <Dropdown.Item
          disabled={!canTriggerStackAction}
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
  return (
    app.status &&
    [
      AppLifecycleStatus.Installing,
      AppLifecycleStatus.InstallFailed,
      AppLifecycleStatus.UpdateFailed,
      AppLifecycleStatus.Installed,
      AppLifecycleStatus.UninstallFailed,
      AppLifecycleStatus.Updating,
      AppDeploymentStatus.Succeeded,
      AppDeploymentStatus.Failed,
    ].includes(app.status)
  );
}

function isBusy(app: ApplicationDeployment) {
  return (
    app.status &&
    [
      AppLifecycleStatus.Installing,
      AppLifecycleStatus.Uninstalling,
      AppLifecycleStatus.Updating,
      AppDeploymentStatus.InProgress,
    ].includes(app.status)
  );
}
