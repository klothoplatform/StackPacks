import type { FC } from "react";
import React, { useState } from "react";
import useApplicationStore from "../pages/store/ApplicationStore.ts";
import { useEffectOnMount } from "../hooks/useEffectOnMount.ts";
import { sumCosts } from "../shared/models/Project.ts";
import { Container } from "./Container.tsx";
import { AiOutlineLoading } from "react-icons/ai";
import classNames from "classnames";
import { FaArrowDown, FaArrowUp } from "react-icons/fa6";

export const CostChange: FC<{
  appIds?: string[];
  operation: "install" | "uninstall";
}> = ({ appIds, operation }) => {
  const { projectCost } = useApplicationStore();
  const [isGettingCost, setIsGettingCost] = useState(false);
  useState<number>(undefined);
  const [cost, setCost] = useState<{
    current?: number;
    pending?: number;
    change?: number;
  }>(undefined);

  useEffectOnMount(() => {
    setIsGettingCost(true);
    (async () => {
      try {
        const response = await projectCost({ operation, appIds });
        const currentTotal = sumCosts(response.current);
        const pendingTotal = sumCosts(response.pending);
        setCost({
          current: currentTotal,
          pending: pendingTotal,
          change: pendingTotal - currentTotal,
        });
      } catch (e) {
        console.error(e);
        setCost(undefined);
      } finally {
        setIsGettingCost(false);
      }
    })();
  });

  return (
    <Container className={"size-fit dark:text-white"}>
      <span
        className={"text-sm font-semibold text-gray-900 dark:text-gray-300"}
      >
        Estimated infrastructure cost{cost?.current > 0 && " change"}
      </span>
      {isGettingCost ? (
        <span className={"flex gap-2 text-gray-500"}>
          <span>Estimating infrastructure cost...</span>
          <AiOutlineLoading className={"animate-spin dark:text-gray-400"} />
        </span>
      ) : !cost || cost.change === undefined ? (
        <span>Cost estimate unavailable</span>
      ) : (
        <div className={"flex h-fit items-center gap-0.5"}>
          <span
            className={classNames("text-xl font-bold flex gap-1 items-center", {
              "text-red-600 dark:text-red-500":
                cost?.current && cost?.change > 0,
              "text-green-600 dark:text-green-500":
                cost?.current && cost?.change < 0,
            })}
          >
            {!cost.current ? (
              ""
            ) : cost.change > 0 ? (
              <FaArrowUp />
            ) : cost.change < 0 ? (
              <FaArrowDown />
            ) : (
              ""
            )}
            ${Math.abs(cost.change ?? 0).toFixed(2)}
          </span>
          <div
            className={
              "whitespace-nowrap pt-0.5 text-xs text-gray-500 dark:text-gray-400"
            }
          >
            / month
          </div>
        </div>
      )}
    </Container>
  );
};
