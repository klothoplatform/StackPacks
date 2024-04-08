import type { CostItem, Project } from "../../shared/models/Project.ts";
import { sumCosts } from "../../shared/models/Project.ts";
import { Button, Table, useThemeMode } from "flowbite-react";
import { useNavigate } from "react-router-dom";
import React, {
  type FC,
  Fragment,
  type PropsWithChildren,
  type ReactNode,
  useEffect,
  useState,
} from "react";
import { Container } from "../../components/Container.tsx";
import classNames from "classnames";
import { FaRegCopy } from "react-icons/fa6";
import { Tooltip } from "../../components/Tooltip.tsx";
import { HiMiniCog6Tooth } from "react-icons/hi2";
import { CollapsibleSection } from "../../components/CollapsibleSection.tsx";
import useApplicationStore from "../store/ApplicationStore.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { AiOutlineLoading } from "react-icons/ai";

export const EnvironmentSection: FC<{ project: Project }> = ({ project }) => {
  const { mode } = useThemeMode();
  const navigate = useNavigate();
  const { currentCost, projectCost } = useApplicationStore();
  const [estimatedCost, setEstimatedCost] = useState<number>(
    currentCost?.length ? sumCosts(currentCost) : undefined,
  );
  const [isRefreshingCost, setIsRefreshingCost] = useState(false);

  useEffect(() => {
    if (currentCost && !currentCost.length) {
      setEstimatedCost(0);
    } else if (currentCost && currentCost.length) {
      setEstimatedCost(sumCosts(currentCost));
    } else {
      setEstimatedCost(undefined);
    }
  }, [currentCost]);

  useEffectOnMount(() => {
    (async () => {
      if (!currentCost) {
        setIsRefreshingCost(true);
        try {
          await projectCost();
        } catch (e) {
          console.error(e);
          setEstimatedCost(undefined);
        } finally {
          setIsRefreshingCost(false);
        }
      }
    })();
  });

  return (
    <>
      <Container className="overflow-auto">
        <div className="flex h-fit w-full flex-col justify-between gap-4 md:flex-row">
          <EnvironmentItem label={"Cloud Provider"}>AWS</EnvironmentItem>
          <EnvironmentItem label={"Region"}>
            {project?.region || "Not set"}
          </EnvironmentItem>
          <EnvironmentItem label={"Deployment Role ARN"}>
            <button
              className="flex flex-col items-start gap-4 lg:flex-row lg:gap-10"
              onClick={() =>
                project?.assumed_role_arn &&
                navigator.clipboard.writeText(project.assumed_role_arn)
              }
            >
              <div className={"flex cursor-pointer flex-nowrap gap-2"}>
                <span
                  className={classNames("w-fit break-all text-xs", {
                    "cursor-pointer": !!project?.assumed_role_arn,
                  })}
                >
                  {project?.assumed_role_arn || "Not set"}
                </span>
                <FaRegCopy className="text-gray-500 dark:text-gray-400" />
              </div>
            </button>
          </EnvironmentItem>
          <EnvironmentItem label={"Estimated Monthly Cost"}>
            {isRefreshingCost ? (
              <span className={"text-gray-500"}>
                <AiOutlineLoading
                  className={"animate-spin dark:text-gray-400"}
                />
              </span>
            ) : estimatedCost === undefined ? (
              <span className={"text-gray-500"}>Not available</span>
            ) : (
              <div className={"flex h-fit items-center gap-0.5"}>
                <span className={"text-3xl font-bold"}>
                  ${estimatedCost.toFixed(2)}
                </span>
                <div
                  className={
                    "text-gray-500: whitespace-nowrap pt-2 text-xs dark:text-gray-400"
                  }
                >
                  / month
                </div>
              </div>
            )}
          </EnvironmentItem>
          <Tooltip content={"Modify Environment"}>
            <Button
              color={mode}
              className={"ml-auto size-fit"}
              size={"xs"}
              pill
              onClick={() => navigate("./environment")}
            >
              <HiMiniCog6Tooth />
            </Button>
          </Tooltip>
        </div>
        {!!project?.policy && (
          <CollapsibleSection
            size={"xs"}
            color={mode}
            collapsedText={"Show deployment policy"}
            expandedText={"Hide deployment policy"}
            collapsed
          >
            <Container className={"p-0"}>
              <div
                className={
                  "max-h-80 w-full overflow-y-auto whitespace-pre-wrap rounded-lg bg-white p-4 font-mono text-xs text-green-700 dark:bg-gray-800 dark:text-green-200"
                }
              >
                <code>{project?.policy}</code>
              </div>
            </Container>
          </CollapsibleSection>
        )}
      </Container>
      <div className={"pl-4"}>
        <CollapsibleSection
          collapsed
          collapsedText={"Show cost breakdown"}
          expandedText={"Hide cost breakdown"}
          color={mode}
          trigger={({ isOpen }) => (
            <div
              className={
                "py-2 text-sm text-blue-600 hover:underline dark:text-blue-400"
              }
            >
              {isOpen ? "Hide" : "Show"} cost breakdown
            </div>
          )}
        >
          <CostTable costs={currentCost || []} />
        </CollapsibleSection>
      </div>
    </>
  );
};

const EnvironmentItem: FC<
  PropsWithChildren<{
    label: string | ReactNode;
  }>
> = (props) => {
  return (
    <div className="flex flex-col items-start gap-2">
      <span className={"text-xs font-medium text-gray-700 dark:text-gray-400"}>
        {props.label}
      </span>
      <div
        className={
          "flex h-full w-fit items-center text-sm text-gray-800 dark:text-gray-200"
        }
      >
        {props.children}
      </div>
    </div>
  );
};

const CostTable: FC<{ costs: CostItem[] }> = ({ costs }) => {
  const computeCosts = [];
  const networkCosts = [];
  const remainingCosts = [];
  costs.forEach((cost) => {
    switch (cost.category) {
      case "compute":
        computeCosts.push(cost);
        break;
      case "network":
        networkCosts.push(cost);
        break;
      default:
        remainingCosts.push(cost);
    }
  });

  const renderTable = (costs: CostItem[], title: string) => {
    const hasAppId = costs.some((cost) => cost.app_id);
    return (
      <Table className={"w-fit"}>
        <Table.Head>
          <Table.HeadCell className={"text-lg"}>{title}</Table.HeadCell>
          {hasAppId && <Table.HeadCell></Table.HeadCell>}
          <Table.HeadCell className={"flex justify-end"}>
            <div className={"flex flex-col text-xs"}>
              <span>Total</span>
              <div className={"flex"}>
                <span className={"font-bold"}>
                  $
                  {costs
                    .reduce((acc, cost) => acc + cost.monthly_cost, 0)
                    .toFixed(2)}
                </span>
                <span className={"font-normal text-gray-500"}>/month</span>
              </div>
            </div>
          </Table.HeadCell>
        </Table.Head>
        <Table.Body>
          <Table.Row>
            {hasAppId && (
              <Table.Cell
                className={
                  "bg-gray-50 pb-1 pt-2 font-medium text-gray-800 dark:bg-gray-700 dark:text-gray-200"
                }
              >
                Application
              </Table.Cell>
            )}
            <Table.Cell
              className={
                "bg-gray-50 pb-1 pt-2 font-medium text-gray-800 dark:bg-gray-700 dark:text-gray-200"
              }
            >
              Category
            </Table.Cell>
            <Table.Cell
              className={
                "bg-gray-50 pb-1 pt-2 font-medium text-gray-800 dark:bg-gray-700 dark:text-gray-200"
              }
            >
              Monthly Cost
            </Table.Cell>
          </Table.Row>
          {costs.map((cost, index) => (
            <Fragment key={index}>
              <Table.Row>
                {hasAppId && <Table.Cell>{cost.app_id}</Table.Cell>}
                <Table.Cell>
                  {cost.category || cost.resource.split(":")[1]}
                </Table.Cell>
                <Table.Cell>${cost.monthly_cost.toFixed(2)}</Table.Cell>
              </Table.Row>
            </Fragment>
          ))}
        </Table.Body>
      </Table>
    );
  };

  return (
    <Container className={"w-fit gap-4"}>
      {renderTable(
        [...computeCosts, ...networkCosts],
        "Shared Infrastructure Costs",
      )}
      {renderTable(remainingCosts, "Application Infrastructure Costs")}
    </Container>
  );
};
