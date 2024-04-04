import type { FC } from "react";
import Ansi from "ansi-to-react-18";
import { Container, ContainerHeader } from "./Container.tsx";

export const StatusReasonCard: FC<{ message: string }> = ({ message }) => {
  return (
    <Container className="max-h-96">
      <ContainerHeader>Status Reason</ContainerHeader>
      <div className="h-fit max-h-64 w-full overflow-auto whitespace-break-spaces font-mono text-sm text-gray-700 dark:text-gray-400">
        <Ansi>{message}</Ansi>
      </div>
    </Container>
  );
};
