import { Button } from "flowbite-react";
import type { ButtonSizes } from "flowbite-react/lib/esm/components/Button/Button";
import type { FC } from "react";
import { useState } from "react";
import { FaCheck, FaRegCopy } from "react-icons/fa6";
import type { FlowbiteColors } from "flowbite-react/lib/esm/components/Flowbite";

export const CopyToClipboardButton: FC<{
  className?: string;
  size?: keyof ButtonSizes;
  color?: keyof FlowbiteColors;
  text: string;
}> = ({ text, size, color, className }) => {
  size = size || "xs";
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <Button
      title="Copy policy to clipboard"
      color={color}
      size={size}
      onClick={copyToClipboard}
      className={className}
    >
      {copied ? (
        <FaCheck className={"text-green-500 dark:text-green-400"} />
      ) : (
        <FaRegCopy />
      )}
    </Button>
  );
};
