import type { FC } from "react";
import React, { useEffect, useState } from "react";
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
import { resolveStackpacks } from "../../../shared/models/Stackpack.ts";
import { BsThreeDotsVertical } from "react-icons/bs";
import { Tooltip } from "../../../components/Tooltip.tsx";
import { useClickedOutside } from "../../../hooks/useClickedOutside.ts";
import type { ApplicationDeployment } from "../../../shared/models/Project.ts";
import {
  AppLifecycleStatus,
  hasDeploymentInProgress,
  toAppStatusString,
} from "../../../shared/models/Project.ts";
import AWSLogoLight from "/images/Amazon_Web_Services_Logo.svg";
import AWSLogoDark from "/images/aws_logo_white.png";
import { outlineBadge } from "../../../shared/custom-themes.ts";
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
import { useEffectOnMount } from "../../../hooks/useEffectOnMount.ts";

export const ProjectPage: FC = () => {
  const { project, getProject, stackPacks } = useApplicationStore();

  const [isRefreshing, setIsRefreshing] = useState(false);

  const { mode } = useThemeMode();
  const AWSLogo = mode === "dark" ? AWSLogoDark : AWSLogoLight;
  const navigate = useNavigate();
  const [refreshInterval, setRefreshInterval] = useState(30 * 1000);

  useDocumentTitle("Project Dashboard");

  useEffect(() => {
    if (hasDeploymentInProgress(project)) {
      setRefreshInterval(8 * 1000);
    } else {
      setRefreshInterval(30 * 1000);
    }
  }, [project]);

  useInterval(async () => {
    if (hasDeploymentInProgress(project)) {
      setIsRefreshing(true);
      try {
        await getProject(true);
      } finally {
        setIsRefreshing(false);
      }
    }
  }, refreshInterval);

  const onRefresh = async () => {
    setIsRefreshing(true);
    try {
      await getProject(true);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffectOnMount(() => {
    onRefresh();
  });

  return (
    <div className="flex size-full flex-col gap-4 overflow-y-auto pr-4">
      <div className={"flex h-fit w-full justify-between py-1"}>
        <div className={"flex h-fit gap-1"}>
          <h2 className={"font-md text-xl"}>Your Project</h2>
          <StackActions />
        </div>
        <Button
          title={"Refresh Project"}
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
        <Card>
          <div className="flex h-fit w-full justify-between p-4">
            <div className="flex gap-4">
              <ul className="flex flex-col text-sm">
                <li className={"flex h-fit items-center gap-1"}>
                  <span>Provider:</span>
                  <img className={"h-3"} src={AWSLogo} alt="AWS" />
                </li>
                <li>
                  <span>Region: {project?.region || "Not set"}</span>
                </li>
                <li>
                  <span>
                    Deployment Role ARN:{" "}
                    {project?.assumed_role_arn || "Not set"}
                  </span>
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
                      {project?.policy}
                    </Card>
                  </CollapsibleSection>
                </li>
              </ul>
            </div>
            <Tooltip content={"Modify Environment"}>
              <Button
                color={mode}
                className={"size-fit"}
                size={"xs"}
                pill
                onClick={() => navigate(`/project/environment`)}
              >
                <HiMiniCog6Tooth />
              </Button>
            </Tooltip>
          </div>
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
        {project && (
          <div className="flex size-full flex-col gap-4">
            {Object.entries(project.stack_packs).map(
              ([appTemplateId, appDeployment], index) => {
                const name =
                  resolveStackpacks([appTemplateId], stackPacks)[0]?.name ??
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

const AppStatusBadge: FC<{
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

const AppCard: FC<{ app: AppCardProps }> = ({ app }) => {
  const { mode } = useThemeMode();
  const appTemplateId = app.app_id;
  return (
    <Card className="flex h-fit w-full flex-col p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center">
          <AppLogo className={"h-fit w-6"} appId={appTemplateId} mode={mode} />
          <h4 className={"font-md ml-2 mr-4"}>{app.name}</h4>
        </div>
        <div className="flex items-center gap-8">
          <AppStatusBadge status={app.status} rtl />
          <AppButtonGroup {...app} />
        </div>
      </div>
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
      await removeApp(app.app_id);
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

  const onInstallApp = async () => {
    try {
      const response = await installApp(app.app_id);
      navigate(
        `/project/apps/${response.app_id}/workflows/${response.workflow_type.toLowerCase()}/runs/${response.run_number}`,
      );
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
            onClick={() => navigate(`./apps/${app.app_id}/configure`)}
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
                  navigate(`/project/apps/${app.app_id}/workflows`);
                }}
              >
                View Workflows
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
          prompt={`Are you sure you want to remove ${app.name} from your project?`}
          confirmationText={"remove"}
          onConfirm={onRemoveApp}
        />
      )}
    </>
  );
};

const StackActions: FC = () => {
  const { installProject, project } = useApplicationStore();
  const [showUninstallAllModal, setShowUninstallAllModal] = useState(false);

  const canTriggerStackAction = project && !hasDeploymentInProgress(project);
  const navigate = useNavigate();

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
          onClick={async () => {
            const response = await installProject();
            navigate(
              `/project/workflows/${response.workflow_type.toLowerCase()}/runs/${response.run_number}`,
            );
          }}
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
    ].includes(app.status)
  );
}
