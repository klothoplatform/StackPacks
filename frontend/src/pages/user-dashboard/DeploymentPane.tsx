import type { FC } from "react";
import { useEffect, useState } from "react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import useApplicationStore from "../store/ApplicationStore.ts";
import { Card } from "flowbite-react";

export const DeploymentPane: FC = () => {
  useDocumentTitle("StackSnap - Deployment Logs");

  const { getDeployments } = useApplicationStore();

  const [deployments, setDeployments] = useState([]);

  useEffect(() => {
    getDeployments().then((deployments) => {
      setDeployments(deployments);
    });
  }, [getDeployments]);

  return (
    <div className="container flex max-w-screen-2xl flex-col items-center justify-center gap-6 overflow-auto px-6">
      <h1>Deployments</h1>
      <ul className={"flex size-full flex-col gap-4"}>
        {deployments.map((deployment, i) => (
          <li key={i}>
            <Card className={"flex items-center justify-center p-4"}>
              <code className={"whitespace-pre-wrap font-mono text-xs"}>
                {JSON.stringify(deployment, undefined, 2)}
              </code>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
};
