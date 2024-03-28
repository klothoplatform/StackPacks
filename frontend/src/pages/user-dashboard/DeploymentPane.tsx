import type { FC } from "react";
import { useEffect, useState } from "react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import useApplicationStore from "../store/ApplicationStore.ts";
import { Card } from "flowbite-react";

export const DeploymentPane: FC = () => {
  useDocumentTitle("StackSnap - Deployment Logs");

  const { getDeployments, getWorkflowExecutions } = useApplicationStore();
  const [workflowExecutions, setWorkflowExecutions] = useState([]);

  const [deployments, setDeployments] = useState([]);

  useEffect(() => {
    (async () => {
      const deployments = await getDeployments();
      const workflowExecutions = await getWorkflowExecutions();
      setDeployments(deployments);
      setWorkflowExecutions(workflowExecutions);
    })();
  }, [getDeployments, getWorkflowExecutions]);

  return (
    <div className="h-full max-w-screen-2xl overflow-auto px-6">
      <div className="flex flex-col items-center justify-center gap-4">
        <h1>Workflow Executions</h1>
        <ul className={"flex size-full flex-col gap-4"}>
          {workflowExecutions.map((execution, i) => (
            <li key={i}>
              <Card className={"flex items-center justify-center p-4"}>
                <code className={"whitespace-pre-wrap font-mono text-xs"}>
                  {JSON.stringify(execution, undefined, 2)}
                </code>
              </Card>
            </li>
          ))}
        </ul>

        <h1>Workflow Steps</h1>
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
    </div>
  );
};
