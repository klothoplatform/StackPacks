import React, {
  type FC,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { useLocation } from "react-router-dom";
import useApplicationStore from "../../store/ApplicationStore.ts";
import type { CustomFlowbiteTheme } from "flowbite-react";
import { Button, Card, Dropdown, TextInput } from "flowbite-react";
import Ansi from "ansi-to-react-18";
import type { EventSourceMessage } from "@microsoft/fetch-event-source";
import {
  AbortError,
  DeployLogEventType,
} from "../../../api/SubscribeToLogStream.ts";
import { AiOutlineLoading3Quarters } from "react-icons/ai";
import "./ansi.scss";
import { useScrollToAnchor } from "../../../hooks/useScrollToAnchor.ts";
import classNames from "classnames";
import { MdSearch } from "react-icons/md";
import {
  HiChevronDown,
  HiChevronUp,
  HiOutlineCog6Tooth,
} from "react-icons/hi2";
import type { VirtuosoHandle } from "react-virtuoso";
import { Virtuoso } from "react-virtuoso";
import { GrLinkBottom } from "react-icons/gr";
import type {
  WorkflowJob,
  WorkflowType,
} from "../../../shared/models/Workflow.ts";
import { toWorkflowJobStatusString } from "../../../shared/models/Workflow.ts";
import { useInterval } from "usehooks-ts";
import { utcToZonedTime } from "date-fns-tz";
import {
  getDurationString,
  getLocalTimezone,
} from "../../../shared/time-util.ts";

type SearchResult = {
  lineNumber: number;
  resultNumber: number;
  start: number;
  end: number;
  selected?: boolean;
};

export const LogViewer: FC<{
  workflowType: WorkflowType;
  runNumber: number;
  appId?: string;
  job: WorkflowJob;
}> = ({ workflowType, runNumber, appId, job }) => {
  const jobNumber = job.job_number;
  const logPaneRef = React.useRef<HTMLDivElement>(null);
  const { subscribeToLogStream } = useApplicationStore();

  const [done, setDone] = useState(false);

  const [log, setLog] = useState([] as string[]);
  const location = useLocation();
  const selectedLine = location.hash.startsWith("#line:")
    ? Number(location.hash.slice(6))
    : null;

  const virtuosoRef = React.useRef<VirtuosoHandle>(null);

  const [results, setResults] = useState<{
    total: number;
    resultLineNumbers: number[];
    items: Map<number, SearchResult[]>;
  }>({ total: 0, items: new Map(), resultLineNumbers: [] });
  const [currentResult, setCurrentResult] = useState(0);

  const onSearchChange = useCallback(
    (search: string) => {
      if (!search) {
        setResults({ total: 0, items: new Map(), resultLineNumbers: [] });
        return;
      } else {
        const newResults = new Map<number, SearchResult[]>();
        let total = 0;
        // find all case-insensitive matches (non-regexp)
        const searchLower = search.toLowerCase();
        const newResultLineNumbers = [];
        log.forEach((line, index) => {
          let start = 0;
          let end = 0;
          // Preprocess the line to remove ANSI escape sequences
          // eslint-disable-next-line no-control-regex
          const ansiEscapeSequenceRegex = /\u001b\[[0-9;]*[A-Za-z]/g;
          let lineLower = line
            .replace(ansiEscapeSequenceRegex, "")
            .toLowerCase();
          while (lineLower.indexOf(searchLower, end) !== -1) {
            start = lineLower.indexOf(searchLower, end);
            end = start + searchLower.length;
            newResults.set(index, [
              ...(newResults.get(index) ?? []),
              {
                resultNumber: total,
                lineNumber: index + 1,
                start,
                end,
              },
            ]);
            newResultLineNumbers[total] = index + 1;
            total++;
          }
        });
        setResults({
          total,
          items: newResults,
          resultLineNumbers: newResultLineNumbers,
        });
        setCurrentResult(0);
        virtuosoRef.current?.scrollToIndex({
          index: newResultLineNumbers[0],
          align: "start",
          behavior: "smooth",
        });
      }
      return results.total;
    },
    [log, results.total],
  );

  useScrollToAnchor({ mode: "auto", behavior: "smooth" });

  useEffect(() => {
    setLog([]);
    if (!workflowType || !jobNumber || !runNumber) {
      return;
    }
    const controller = new AbortController();
    (async () => {
      try {
        await subscribeToLogStream({
          targetedAppId: appId,
          workflowType: workflowType,
          jobNumber: jobNumber,
          runNumber: runNumber,
          listener: (message: EventSourceMessage) => {
            const { event, data } = message;
            if (event === DeployLogEventType.LogLine) {
              setLog((log) => {
                return [...log, data];
              });
            } else if (event === DeployLogEventType.Done) {
              console.log("log stream done");
              controller.abort();
              setDone(true);
            }
          },
          controller,
        });
      } catch (e) {
        if (e instanceof AbortError) {
          console.log("log stream aborted");
        } else {
          throw e;
        }
      }
    })();
    return () => {
      console.log("aborting log stream");
      controller.abort();
    };
  }, [appId, jobNumber, runNumber, subscribeToLogStream, workflowType]);

  const appendInterval = useRef(null);
  const showButtonTimeoutRef = useRef(null);
  const [showBottomButton, setShowBottomButton] = useState(false);
  const [atBottom, setAtBottom] = useState(false);

  useEffect(() => {
    const interval = appendInterval.current;
    return () => {
      clearInterval(interval);
      clearTimeout(showButtonTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    clearTimeout(showButtonTimeoutRef.current);
    if (!atBottom) {
      showButtonTimeoutRef.current = setTimeout(
        () => setShowBottomButton(true),
        500,
      );
    } else {
      setShowBottomButton(false);
    }
  }, [atBottom, setShowBottomButton]);

  const [showLineNumbers, setShowLineNumbers] = useState(true);

  const [duration, setDuration] = useState<number>(null);
  const [interval, setInterval] = useState<number | null>(
    job.initiated_at && !job.completed_at ? 1000 : null,
  );

  useInterval(() => {
    if (job.initiated_at && !job.completed_at) {
      setDuration(
        (Date.now() -
          utcToZonedTime(job.initiated_at, getLocalTimezone()).getTime()) /
          1000,
      );
    }
  }, interval);

  useEffect(() => {
    if (job.initiated_at && job.completed_at) {
      setDuration(
        (utcToZonedTime(job.completed_at, getLocalTimezone()).getTime() -
          utcToZonedTime(job.initiated_at, getLocalTimezone()).getTime()) /
          1000,
      );
      setInterval(null);
    } else if (job.initiated_at && !job.completed_at) {
      setInterval(1000);
    }
  }, [job.initiated_at, job.completed_at]);

  const statusText =
    job.initiated_at && !job.completed_at
      ? getDurationString(duration)
      : toWorkflowJobStatusString(job.status);

  return (
    <div className="flex size-full flex-col items-start justify-start gap-4">
      <Card className="size-full bg-gray-800 p-2 text-white">
        <div
          ref={logPaneRef}
          className={
            "flex size-full flex-col scroll-smooth whitespace-pre-wrap py-2 pr-2 text-xs"
          }
        >
          <div className="flex flex-col justify-start gap-2 border-b border-gray-700 pb-4 md:flex-row md:items-center md:justify-between">
            <div className="flex w-fit flex-col gap-0.5 pl-2">
              <span
                className="line-clamp-1 w-fit overflow-hidden text-ellipsis text-lg font-bold"
                title={job?.title}
              >
                {job?.title ?? "Job"}
              </span>
              <span
                className="line-clamp-1 w-fit truncate text-xs font-light text-gray-400"
                title={statusText}
              >
                {statusText}
              </span>
            </div>
            <div className="mb-2 flex min-w-fit items-center gap-2">
              <div className={"max-w-lg"}>
                <SearchInput
                  mode={"dark"}
                  onUpdate={onSearchChange}
                  onNavigate={(index) => {
                    setCurrentResult(index);
                    virtuosoRef.current?.scrollToIndex({
                      index: results.resultLineNumbers[index] - 1, // 0-based index
                      align: "start",
                      behavior: "smooth",
                    });
                  }}
                />
              </div>
              <Dropdown
                color={"dark"}
                placement={"bottom-end"}
                arrowIcon={false}
                size={"xs"}
                label={
                  <HiOutlineCog6Tooth size={20} className={"text-gray-400"} />
                }
              >
                <Dropdown.Item
                  onClick={() => {
                    setShowLineNumbers(!showLineNumbers);
                  }}
                >
                  {showLineNumbers ? "Hide line numbers" : "Show line numbers"}
                </Dropdown.Item>
              </Dropdown>
            </div>
          </div>
          <Virtuoso
            ref={virtuosoRef}
            followOutput
            totalCount={log.length}
            atBottomStateChange={(bottom) => {
              clearInterval(appendInterval.current);
              setAtBottom(bottom);
            }}
            itemContent={(index) => {
              return (
                <div
                  key={index}
                  className={classNames(
                    "flex h-fit flex-nowrap items-start gap-4 px-2 hover:bg-gray-700",
                    {
                      "bg-primary-600/40": selectedLine === index + 1,
                    },
                  )}
                >
                  <a
                    href={`#line:${index + 1}`}
                    id={`line:${index + 1}`}
                    className={classNames(
                      "font-mono text-gray-400 transition-all hover:text-primary-300 hover:underline select-none",
                      {
                        hidden: !showLineNumbers,
                        "text-primary-300 underline":
                          selectedLine === index + 1,
                      },
                    )}
                  >
                    {index + 1}
                  </a>
                  {!showLineNumbers && <br />}
                  <Ansi linkify useClasses>
                    {highlightSearchResults(
                      log[index],
                      results.items.get(index) ?? [],
                      currentResult,
                    )}
                  </Ansi>
                </div>
              );
            }}
          />
          {showBottomButton && (
            <Button
              size={"xs"}
              color={"dark"}
              className={
                "absolute bottom-16 right-24 float-right size-fit whitespace-nowrap"
              }
              onClick={() =>
                virtuosoRef.current.scrollToIndex({
                  index: "LAST",
                  behavior: "smooth",
                })
              }
            >
              <span className={"flex items-center gap-2"}>
                <GrLinkBottom />
                Scroll to latest
              </span>
            </Button>
          )}
          <span className="mt-4 px-2 font-mono font-bold text-green-300">
            {done ? (
              "Done"
            ) : (
              <AiOutlineLoading3Quarters
                size={11}
                className={"animate-spin text-gray-400"}
              />
            )}
          </span>
        </div>
      </Card>
    </div>
  );
};

function highlightSearchResults(
  lineContent: string,
  results: SearchResult[],
  currentResult: number,
) {
  if (results.length === 0) {
    return lineContent;
  }

  // Preprocess the line to remove ANSI escape sequences
  // eslint-disable-next-line no-control-regex
  const ansiEscapeSequenceRegex = /\u001b\[[0-9;]*[A-Za-z]/g;
  const preprocessedLineContent = lineContent.replace(
    ansiEscapeSequenceRegex,
    "",
  );

  // Convert the line to an array of characters
  let chars = Array.from(preprocessedLineContent);

  // Loop over the search results
  for (let i = 0; i < results.length; i++) {
    // Get the current search result
    let result = results[i];

    // Wrap the search result in ANSI escape codes
    // If this is the current result, use a different color
    if (results[i].resultNumber === currentResult) {
      chars[result.start] = "\u001b[44m" + chars[result.start];
      chars[result.end - 1] = chars[result.end - 1] + "\u001b[49m";
    } else {
      chars[result.start] = "\u001b[48;5;240m" + chars[result.start];
      chars[result.end - 1] = chars[result.end - 1] + "\u001b[49m";
    }
  }

  // Join the characters back together and return the result
  return chars.join("");
}

const searchNavButtonTheme: CustomFlowbiteTheme["button"] = {
  base: "group flex items-stretch items-center justify-center p-0.5 text-center font-medium relative focus:z-10 focus:outline-none transition-[color,background-color,border-color,text-decoration-color,fill,stroke,box-shadow]",
  size: {
    xs: "text-xs p-1",
  },
  color: {
    dark: "text-white bg-gray-900 border border-transparent enabled:hover:bg-gray-800 focus:ring-4 focus:ring-primary-300 dark:bg-gray-700 dark:enabled:hover:bg-gray-900 dark:focus:ring-gray-700 dark:border-gray-700",
    light:
      "text-gray-900 bg-bg-gray-50 border border-gray-50 enabled:hover:bg-gray-100 focus:ring-4 focus:ring-primary-300 dark:bg-gray-600 dark:text-white dark:border-gray-600 dark:enabled:hover:bg-gray-700 dark:enabled:hover:border-gray-700 dark:focus:ring-gray-700",
  },
};

const SearchInput: React.FC<{
  onUpdate?: (query: string) => number | Promise<number>;
  onNavigate?: (index: number) => void;
  mode?: "light" | "dark" | string;
}> = ({ onUpdate, onNavigate, mode }) => {
  const [query, setQuery] = useState<string>("");
  const [resultCount, setResultCount] = useState<number>(0);
  const [currentResult, setCurrentResult] = useState(0);

  mode = mode === "dark" ? "dark" : "light";

  useEffect(() => {
    (async () => {
      setCurrentResult(0);
      setResultCount(await onUpdate?.(query));
    })();
  }, [query, onUpdate]);

  return (
    <div
      className={classNames("flex items-center gap-2 sm:w-full", {
        dark: mode === "dark",
      })}
    >
      <TextInput
        theme={{
          field: {
            input: {
              base: "block w-full border disabled:cursor-not-allowed disabled:opacity-50 pr-24",
              sizes: {
                sm: "pl-2 py-2 sm:text-xs",
                md: "pl-2.5 py-2.5 text-sm",
                lg: "sm:text-md pl-4 py-4",
              },
            },
          },
        }}
        sizing={"sm"}
        type="text"
        placeholder="Search logs"
        icon={MdSearch}
        className="w-full"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key !== "Enter") {
            return;
          }
          if (currentResult < resultCount - 1) {
            setCurrentResult(currentResult + 1);
            onNavigate(currentResult + 1);
          } else {
            setCurrentResult(0);
            onNavigate(0);
          }
        }}
      />
      {resultCount > 0 && (
        <div
          className={"absolute right-[6.5rem] flex w-fit items-center gap-2"}
        >
          <span className={"text-xs font-light text-gray-400"}>
            {currentResult + 1}/{resultCount}
          </span>
          <div className={"flex gap-0.5"}>
            <Button
              theme={searchNavButtonTheme}
              size={"xs"}
              color={mode}
              onClick={() => {
                const nextResult =
                  currentResult >= resultCount - 1 ? 0 : currentResult + 1;
                setCurrentResult(nextResult);
                onNavigate?.(nextResult);
              }}
            >
              <HiChevronDown />
            </Button>
            <Button
              theme={searchNavButtonTheme}
              size={"xs"}
              color={mode}
              onClick={() => {
                const prevResult =
                  currentResult <= 1 ? resultCount - 1 : currentResult - 1;
                setCurrentResult(prevResult);
                onNavigate?.(prevResult);
              }}
            >
              <HiChevronUp />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
