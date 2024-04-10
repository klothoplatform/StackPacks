import type { FC } from "react";
import React, { Fragment, useState } from "react";
import type { CostItem, Project } from "../../shared/models/Project.ts";
import { Accordion, Table } from "flowbite-react";
import { titleCase } from "title-case";
import { flatTable } from "../../shared/custom-themes.ts";
import { SortableHeaderCell } from "../../components/SortableHeaderCell.tsx";

export const CostTable: FC<{ project: Project; costs: CostItem[] }> = ({
  project,
  costs,
}) => {
  const computeCosts = [];
  const networkCosts = [];
  const otherCommonCosts = [];
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
        if (!cost.app_id || cost.app_id === "common") {
          otherCommonCosts.push(cost);
        } else {
          remainingCosts.push(cost);
        }
    }
  });
  const commonCosts = [...computeCosts, ...networkCosts, ...otherCommonCosts];

  const [sortedBy, setSortedBy] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const updateSort = (sort: string) => {
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
  };

  const renderTable = (
    costs: CostItem[],
    title: string,
    hideAppId?: boolean,
  ) => {
    costs = costs?.filter((cost) => cost.monthly_cost > 0);
    const hasAppId = costs.some((cost) => cost.app_id);
    return (
      <Accordion.Panel>
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
                    {costs
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
          <Table
            theme={flatTable}
            className={"border-separate border-spacing-0"}
          >
            <Table.Head
              className={
                "sticky top-0 overflow-x-clip bg-white dark:bg-gray-900 [&_th]:border-b dark:[&_th]:border-gray-700"
              }
            >
              {hasAppId && !hideAppId && (
                <SortableHeaderCell
                  sortedBy={sortedBy}
                  updateSort={updateSort}
                  id={"app_id"}
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
                colSpan={hasAppId && !hideAppId ? 1 : 2}
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
              {costs.map((cost, index) => (
                <Fragment key={index}>
                  <Table.Row>
                    {hasAppId && !hideAppId && (
                      <Table.Cell
                        className={
                          sortedBy === "app_id"
                            ? "bg-gray-50 dark:bg-gray-800"
                            : ""
                        }
                      >
                        {project.stack_packs[cost.app_id]?.display_name ||
                          cost.app_id}
                      </Table.Cell>
                    )}
                    <Table.Cell
                      className={
                        sortedBy === "category"
                          ? "bg-gray-50 dark:bg-gray-800"
                          : ""
                      }
                      colSpan={hasAppId && !hideAppId ? 1 : 2}
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
                          cost.resource.split(":")[1].replaceAll("_", " ") ||
                            "",
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

  const compareRows = (a: CostItem, b: CostItem) =>
    !sortedBy
      ? 0
      : sortDirection === "desc"
        ? compareValues(b[sortedBy], a[sortedBy])
        : compareValues(a[sortedBy], b[sortedBy]);

  return (
    <Accordion className={"mb-4"}>
      {(computeCosts.length > 0 || networkCosts.length > 0) &&
        renderTable(
          commonCosts.sort(compareRows),
          "Shared Infrastructure Costs",
          true,
        )}
      {remainingCosts.length > 0 &&
        renderTable(
          remainingCosts.sort(compareRows),
          "Application Infrastructure Costs",
        )}
    </Accordion>
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
