import { MdExpandMore } from "react-icons/md";
import classNames from "classnames";
import type { FC, PropsWithChildren, ReactNode } from "react";
import React, { useCallback, useState } from "react";
import type { IconType } from "react-icons";
import type { FlowbiteColors, FlowbiteSizes } from "flowbite-react";
import { Button } from "flowbite-react";

interface CollapsibleSectionProps {
  collapsedText?: ReactNode;
  expandedText?: ReactNode;
  trigger?: FC<{ isOpen?: boolean }>;
  icon?: IconType;
  color?: keyof FlowbiteColors;
  placement?:
    | "left"
    | "right"
    | "top-left"
    | "top-right"
    | "bottom-left"
    | "bottom-right";
  outline?: boolean;
  pill?: boolean;
  size?: keyof FlowbiteSizes;
  onExpand?: () => Promise<void>;
  onCollapse?: () => void;
  collapsed?: boolean;
  renderCollapsed?: boolean;
  className?: string;
}

export const CollapsibleSection: FC<
  PropsWithChildren<CollapsibleSectionProps>
> = ({
  expandedText,
  collapsedText,
  color,
  placement,
  trigger,
  icon,
  children,
  outline,
  pill,
  onCollapse,
  onExpand,
  size,
  collapsed,
  renderCollapsed,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(!collapsed);

  const CustomTrigger = trigger;
  const isTop = !placement?.startsWith("bottom");
  const isLeft = placement?.endsWith("left");
  const isRight = placement?.endsWith("right");

  const ResolvedTrigger = useCallback(() => {
    const onClick = async (isOpen: boolean) => {
      setIsOpen(!isOpen);
      if (isOpen) {
        onCollapse?.();
      } else {
        await onExpand?.();
      }
    };
    return (
      <div
        className={classNames("size-fit", {
          "ml-auto": isRight,
          "mr-auto": isLeft,
        })}
      >
        {CustomTrigger ? (
          <button onClick={() => onClick(isOpen)}>
            <CustomTrigger isOpen={isOpen} />
          </button>
        ) : (
          <DefaultTrigger
            onClick={() => onClick(isOpen)}
            isOpen={isOpen}
            icon={icon}
            collapsedText={collapsedText}
            expandedText={expandedText}
            color={color}
            outline={outline}
            pill={pill}
            size={size}
          />
        )}
      </div>
    );
  }, [
    CustomTrigger,
    collapsedText,
    color,
    expandedText,
    icon,
    isLeft,
    isOpen,
    isRight,
    onCollapse,
    onExpand,
    outline,
    pill,
    size,
  ]);

  return (
    <>
      {isTop && <ResolvedTrigger />}
      {(isOpen || renderCollapsed) && (
        <div className={className} hidden={!isOpen && renderCollapsed}>
          {children}
        </div>
      )}
      {!isTop && <ResolvedTrigger />}
    </>
  );
};

const DefaultTrigger: FC<{
  onClick: () => void;
  isOpen: boolean;
  icon?: IconType;
  collapsedText?: ReactNode;
  expandedText?: ReactNode;
  color?: keyof FlowbiteColors;
  outline?: boolean;
  pill?: boolean;
  size?: keyof FlowbiteSizes;
}> = ({
  onClick,
  isOpen,
  icon,
  collapsedText,
  expandedText,
  color,
  outline,
  pill,
  size,
}) => {
  collapsedText = collapsedText || "Show more";
  expandedText = expandedText || "Show less";
  color = color === undefined ? "info" : color;
  const Icon = icon || MdExpandMore;
  return (
    <Button
      color={color as string}
      className={
        "my-2 flex w-fit cursor-pointer items-center justify-between gap-2"
      }
      outline={outline}
      pill={pill}
      size={size}
      onClick={onClick}
    >
      <h3 className="mr-2 font-medium">
        {isOpen ? expandedText : collapsedText}
      </h3>
      <Icon
        size={24}
        className={classNames({
          "transform rotate-180": isOpen,
        })}
      />
    </Button>
  );
};
