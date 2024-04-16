import type { FC } from "react";
import React, { useEffect, useState } from "react";
import useApplicationStore from "../store/ApplicationStore.ts";
import { UIError } from "../../shared/errors.ts";
import { Button, Dropdown, useThemeMode } from "flowbite-react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import { useNavigate } from "react-router-dom";
import { AiFillDelete, AiFillEye } from "react-icons/ai";
import classNames from "classnames";
import { BsThreeDotsVertical } from "react-icons/bs";
import { Tooltip } from "../../components/Tooltip.tsx";
import { useClickedOutside } from "../../hooks/useClickedOutside.ts";
import type { ApplicationDeployment } from "../../shared/models/Project.ts";
import {
  AppLifecycleStatus,
  hasDeploymentInProgress,
} from "../../shared/models/Project.ts";
import {
  RiExternalLinkLine,
  RiInstallFill,
  RiUninstallFill,
} from "react-icons/ri";
import UninstallAppModal from "./UninstallAppModal.tsx";
import { ConfirmationModal } from "../../components/ConfirmationModal.tsx";
import UninstallAllModal from "./UninstallAllModal.tsx";
import { HiMiniCog6Tooth } from "react-icons/hi2";
import { AppLogo } from "../../components/AppLogo.tsx";
import { useInterval } from "usehooks-ts";
import { IoRefresh } from "react-icons/io5";
import { SlRefresh } from "react-icons/sl";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { EnvironmentSection } from "./EnvironmentSection.tsx";
import { hasMapping } from "../../shared/LogoMappings.tsx";
import { Container } from "../../components/Container.tsx";
import { AppStatusBadge } from "../../components/AppStatusBadge.tsx";

export const ProjectPage: FC = () => {
  const { project, getProject, stackPacks } = useApplicationStore();

  const [isRefreshing, setIsRefreshing] = useState(false);

  const { mode } = useThemeMode();
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
        <EnvironmentSection project={project} />
      </div>
      <div className="flex flex-col gap-1">
        <div className={"flex w-full items-baseline justify-between gap-4"}>
          <h3 className={"font-md text-lg"}>Apps</h3>
          <Button
            pill
            size={"xs"}
            color={"purple"}
            onClick={() => navigate("./add-apps")}
          >
            <span>+ Add new</span>
          </Button>
        </div>
        {project && (
          <div className="flex size-full flex-col gap-4">
            {Object.values(project.stack_packs)
              .filter((appDeployment) => appDeployment.app_id !== "common")
              .map((appDeployment, index) => {
                const status =
                  appDeployment.status ?? AppLifecycleStatus.Uninstalled;
                const app = { ...appDeployment, status };
                return <AppCard key={index} app={app} />;
              })}
          </div>
        )}
      </div>
    </div>
  );
};

const AppCard: FC<{ app: ApplicationDeployment }> = ({ app }) => {
  const { mode } = useThemeMode();
  const appTemplateId = app.app_id;
  return (
    <Container className="flex h-fit w-full flex-col p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className={"size-4"}>
            {hasMapping(appTemplateId) ? (
              <AppLogo
                className={"max-h-4 max-w-4"}
                appId={appTemplateId}
                mode={mode}
              />
            ) : (
              " "
            )}
          </span>
          <Tooltip
            content={`Open ${app.display_name}`}
            disabled={!app.outputs?.URL}
          >
            <h4
              className={classNames("text-lg font-medium", {
                "hover:text-blue-600 hover:underline dark:hover:text-blue-400":
                  app.outputs?.URL,
              })}
            >
              {app.outputs?.URL ? (
                <a
                  className={"flex cursor-pointer items-center gap-2"}
                  href={`${app.outputs.URL.match(/^https?:\/\//) ? "" : "http://"}${app.outputs.URL}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  {app.display_name}
                  <RiExternalLinkLine />
                </a>
              ) : (
                app.display_name
              )}
            </h4>
          </Tooltip>
        </div>
        <div className="flex items-center gap-8">
          <AppStatusBadge status={app.status} rtl />
          <AppButtonGroup app={app} />
        </div>
      </div>
    </Container>
  );
};

const AppButtonGroup: FC<{ app: ApplicationDeployment }> = ({ app }) => {
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
          message: `Removing ${app.display_name} failed!`,
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
          message: `Installing ${app.display_name} failed!`,
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
                  Install {app.display_name}
                </Dropdown.Item>
              )}
              {isInstalled(app) && (
                <Dropdown.Item
                  disabled={isBusy(app)}
                  icon={IoRefresh}
                  onClick={() => onInstallApp()}
                >
                  Redeploy {app.display_name}
                </Dropdown.Item>
              )}
              {isInstalled(app) && (
                <Dropdown.Item
                  disabled={isBusy(app)}
                  icon={RiUninstallFill}
                  color={"red"}
                  onClick={() => setShowUninstallModal(true)}
                >{`Uninstall ${app.display_name}`}</Dropdown.Item>
              )}
              {!isInstalled(app) && !isBusy(app) && (
                <Dropdown.Item
                  icon={AiFillDelete}
                  onClick={() => setShowRemoveModal(true)}
                >{`Remove ${app.display_name}`}</Dropdown.Item>
              )}
            </div>
          </Dropdown>
        </Tooltip>
      </div>
      {showUninstallModal && (
        <UninstallAppModal
          onClose={() => setShowUninstallModal(false)}
          id={app.app_id}
          name={app.display_name}
        />
      )}
      {showRemoveModal && (
        <ConfirmationModal
          cancelable
          title={`Remove "${app.display_name}"`}
          onClose={() => setShowRemoveModal(false)}
          confirmButtonLabel={"Remove"}
          prompt={`Are you sure you want to remove ${app.display_name} from your project?`}
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
