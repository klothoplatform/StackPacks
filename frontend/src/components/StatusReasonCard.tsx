import type { FC } from "react";
import Ansi from "ansi-to-react-18";

export const StatusReasonCard: FC<{ message: string }> = ({ message }) => {
  return (
    <div className="max-h-96 w-full rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
      <div className="h-fit max-h-64 w-full overflow-auto whitespace-break-spaces font-mono text-sm text-gray-700 dark:text-gray-400">
        <Ansi>{message}</Ansi>
      </div>
    </div>
  );
};
