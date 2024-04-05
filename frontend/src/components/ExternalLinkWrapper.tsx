import type { FC, PropsWithChildren } from "react";
import React from "react";
import { RiExternalLinkLine } from "react-icons/ri";

export const ExternalLinkWrapper: FC<PropsWithChildren> = ({ children }) => {
  return (
    <span className="flex items-center gap-1 text-blue-600 hover:underline dark:text-blue-400">
      {children} <RiExternalLinkLine />
    </span>
  );
};
