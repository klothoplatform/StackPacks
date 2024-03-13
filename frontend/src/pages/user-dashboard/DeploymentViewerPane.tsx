import { useState, type FC, useEffect } from "react";
import { useDocumentTitle } from "../../hooks/useDocumentTitle.ts";
import { useNavigate, useParams } from "react-router-dom";
import useApplicationStore from "../store/ApplicationStore.ts";
import { useEffectOnMount } from "../../hooks/useEffectOnMount.ts";
import { UIError } from "../../shared/errors.ts";
import { Tabs } from "flowbite-react";

export const DeploymentViewerPane: FC = () => {
  useDocumentTitle("StackPacks - Log Viewer");
  const { deployId, appId } = useParams();

  const { getUserStack, addError, deployLogs } = useApplicationStore();

  const navigate = useNavigate();

  const [applications, setApplications] = useState([] as string[]);

  if (!deployId) {
    navigate(`..`);
  }

  useEffectOnMount(() => {
    (async () => {
      try {
        const stack = await getUserStack();
        const apps = Object.keys(stack.stack_packs);
        apps.push("common");
        apps.sort();
        setApplications(apps);
      } catch (e) {
        addError(
          new UIError({
            message: "Failed to load user stack",
            cause: e,
          }),
        );
      }
    })();
  });

  useEffect(() => {
    if (!appId && applications.length > 0 && applications[0] !== undefined) {
      navigate(`/user/dashboard/deploy/${deployId}/app/${applications[0]}`);
    }
  }, [appId, deployId, applications]);

  const [log, setLog] = useState([] as string[]);

  useEffect(() => {
    setLog([]);
    async function fetchLogs() {
      const resp = await deployLogs(deployId, appId);
      resp.addEventListener("message", (data) => {
        setLog((log) => [...log, data.data]);
      });
      resp.addEventListener("done", () => {
        resp.close();
      });
      return resp;
    }
    const resp = fetchLogs();
    return () => {
      resp.then((r) => r.close());
    };
  }, [deployId, appId]);

  const changeTab = (tab) => {
    const app = applications[tab];
    if (app !== appId && app !== undefined) {
      navigate(`/user/dashboard/deploy/${deployId}/app/${app}`);
    }
  };

  return (
    <Tabs style="underline" onActiveTabChange={changeTab}>
      {applications.map((app) => {
        if (app !== appId) {
          return <Tabs.Item key={app} title={app} />;
        } else {
          return (
            <Tabs.Item key={app} active title={app}>
              <div
                className="overflow-auto dark:bg-gray-800"
                style={{ height: "80vh" }}
              >
                {log.map((line, lino) => (
                  <div key={lino.toString()}>{line.trimEnd()}</div>
                ))}
              </div>
            </Tabs.Item>
          );
        }
      })}
    </Tabs>
  );
};
