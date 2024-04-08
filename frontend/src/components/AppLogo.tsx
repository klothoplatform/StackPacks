import type { FC, ImgHTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";
import { LogoMappings } from "../shared/LogoMappings.tsx";

export const AppLogo: FC<
  ImgHTMLAttributes<any> & { appId: string; mode?: string }
> = ({ appId, mode, className, ...rest }) => {
  let mapping = LogoMappings[appId];
  if (!mapping) {
    return null;
  }
  if (typeof mapping === "string") {
    mapping = { filePath: mapping, darkPath: mapping };
  }
  className = twMerge(
    "h-10" +
      (className ? ` ${className}` : "") +
      (mapping.className ? ` ${mapping.className}` : ""),
  );

  return (
    <img
      src={
        mode === "dark"
          ? mapping.darkPath ?? mapping.filePath
          : mapping.filePath
      }
      alt={appId}
      className={className}
      {...rest}
    />
  );
};
