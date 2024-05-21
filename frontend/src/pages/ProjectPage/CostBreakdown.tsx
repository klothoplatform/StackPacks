import type { FC } from "react";
import React, { Fragment, useCallback, useEffect, useState } from "react";
import type { CostItem, Project } from "../../shared/models/Project.ts";
import { Accordion, Table } from "flowbite-react";
import { titleCase } from "title-case";
import { flatTable } from "../../shared/custom-themes.ts";
import { SortableHeaderCell } from "../../components/SortableHeaderCell.tsx";
import type { AccordionPanelProps } from "flowbite-react/lib/esm/components/Accordion/AccordionPanel";

interface EnhancedCostItem extends CostItem {
  app_name: string;
}

export const CostBreakdown: FC<{ project: Project; costs: CostItem[] }> = ({
  project,
  costs,
}) => {
  const networkCosts = [];
  const otherCommonCosts = [];
  const remainingCosts = [];
  costs.forEach((cost: EnhancedCostItem) => {
    cost = {
      ...cost,
      app_name: project.stack_packs[cost.app_id]?.display_name || cost.app_id,
    };
    switch (cost.category) {
      case "network":
        networkCosts.push(cost);
        break;
      default:
        if (!cost.app_id || cost.app_id === "common") {
          otherCommonCosts.push(cost);
        } else {
          remainingCosts.push(cost);
        }
    }
  });
  const commonCosts = [...networkCosts, ...otherCommonCosts];

  const tables = [
    {
      costs: commonCosts,
      title: "Shared Infrastructure Costs",
      hideAppName: true,
    },
    {
      costs: remainingCosts,
      title: "Application Infrastructure Costs",
    },
  ]
    .filter(({ costs }) => costs.length)
    .map(({ costs, title, hideAppName }, index) => (
      <CostTable
        costs={costs}
        title={title}
        hideAppName={hideAppName}
        key={index}
      />
    ));

  return (
    <>
      {tables?.length ? (
        <Accordion className={"mb-4"}>{tables}</Accordion>
      ) : undefined}
    </>
  );
};

interface CostTableProps extends Omit<AccordionPanelProps, "children"> {
  costs: EnhancedCostItem[];
  title: string;
  hideAppName?: boolean;
}

const CostTable: FC<CostTableProps> = ({
  costs,
  title,
  hideAppName,
  ...panelProps
}) => {
  const hasAppName = costs.some((cost) => cost.app_id);

  const [sortedBy, setSortedBy] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [sortedCosts, setSortedCosts] = useState<EnhancedCostItem[]>(costs);

  const updateSort = useCallback(
    (sort: string) => {
      if (sortedBy && sortedBy === sort) {
        setSortDirection(sortDirection === "asc" ? "desc" : "asc");
        if (sortDirection === "desc") {
          setSortedBy(null);
          return;
        }
      } else {
        setSortDirection("asc");
        setSortedBy(sort);
      }
    },
    [sortedBy, sortDirection],
  );

  const compareRows = useCallback(
    (a: CostItem, b: CostItem) =>
      !sortedBy
        ? 0
        : sortDirection === "desc"
          ? compareValues(b[sortedBy], a[sortedBy])
          : compareValues(a[sortedBy], b[sortedBy]),
    [sortedBy, sortDirection],
  );

  useEffect(() => {
    setSortedCosts(
      costs.filter((cost) => cost.monthly_cost > 0).sort(compareRows),
    );
  }, [sortedBy, sortDirection, costs, compareRows]);

  return (
    <Accordion.Panel {...panelProps}>
      <Accordion.Title
        theme={{
          heading: "w-full mr-4",
        }}
      >
        <div
          className={
            "flex w-full flex-col gap-2 md:flex-row md:items-center md:justify-between"
          }
        >
          <div className={"text-lg"}>{title}</div>
          <div className={"flex md:ml-auto md:justify-end"}>
            <div className={"flex flex-col text-xs"}>
              <span>Total</span>
              <div className={"flex"}>
                <span className={"font-bold"}>
                  $
                  {sortedCosts
                    .reduce((acc, cost) => acc + cost.monthly_cost, 0)
                    .toFixed(2)}
                </span>
                <span className={"font-normal text-gray-500"}>/month</span>
              </div>
            </div>
          </div>
        </div>
      </Accordion.Title>
      <Accordion.Content
        className={"max-w-full overflow-x-clip bg-white px-0 pb-1.5 pt-2"}
      >
        <Table theme={flatTable} className={"border-separate border-spacing-0"}>
          <Table.Head
            className={
              "sticky top-0 overflow-x-clip bg-white dark:bg-gray-900 [&_th]:border-b dark:[&_th]:border-gray-700"
            }
          >
            {hasAppName && !hideAppName && (
              <SortableHeaderCell
                sortedBy={sortedBy}
                updateSort={updateSort}
                id={"app_name"}
                sortDirection={sortDirection}
              >
                Application
              </SortableHeaderCell>
            )}
            <SortableHeaderCell
              sortedBy={sortedBy}
              updateSort={updateSort}
              sortDirection={sortDirection}
              id={"category"}
              colSpan={hasAppName && !hideAppName ? 1 : 2}
            >
              Category
            </SortableHeaderCell>
            <SortableHeaderCell
              sortedBy={sortedBy}
              updateSort={updateSort}
              sortDirection={sortDirection}
              id={"resource"}
            >
              Resource
            </SortableHeaderCell>
            <SortableHeaderCell
              sortedBy={sortedBy}
              updateSort={updateSort}
              sortDirection={sortDirection}
              id={"monthly_cost"}
            >
              Monthly Cost
            </SortableHeaderCell>
          </Table.Head>
          <Table.Body
            className={
              "[&>tr>td]:border-t [&>tr>td]:border-gray-200 [&>tr>td]:dark:border-gray-700"
            }
          >
            {sortedCosts.map((cost, index) => (
              <Fragment key={index}>
                <Table.Row>
                  {hasAppName && !hideAppName && (
                    <Table.Cell
                      className={
                        sortedBy === "app_name"
                          ? "bg-gray-50 dark:bg-gray-800"
                          : ""
                      }
                    >
                      {cost.app_name}
                    </Table.Cell>
                  )}
                  <Table.Cell
                    className={
                      sortedBy === "category"
                        ? "bg-gray-50 dark:bg-gray-800"
                        : ""
                    }
                    colSpan={hasAppName && !hideAppName ? 1 : 2}
                  >
                    {titleCase(cost.category || "")}
                  </Table.Cell>
                  <Table.Cell
                    className={
                      sortedBy === "resource"
                        ? "bg-gray-50 dark:bg-gray-800"
                        : ""
                    }
                  >
                    {cost.resource &&
                      titleCase(
                        cost.resource.split(":")[1].replaceAll("_", " ") || "",
                      )}
                  </Table.Cell>
                  <Table.Cell
                    className={
                      sortedBy === "monthly_cost"
                        ? "bg-gray-50 dark:bg-gray-800"
                        : ""
                    }
                  >
                    ${cost.monthly_cost.toFixed(2)}
                  </Table.Cell>
                </Table.Row>
              </Fragment>
            ))}
          </Table.Body>
        </Table>
      </Accordion.Content>
    </Accordion.Panel>
  );
};

function compareValues(a: number | string, b: number | string): number {
  if (typeof a === "string" && typeof b === "string") {
    return a.localeCompare(b);
  } else if (typeof a === "number" && typeof b === "number") {
    return a - b;
  } else {
    return `${a}`.localeCompare(`${b}`);
  }
}
