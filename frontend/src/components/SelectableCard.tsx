import type { FC } from "react";
import React, { createContext } from "react";
import { useState } from "react";
import type { CardProps, CustomFlowbiteTheme } from "flowbite-react";
import { Card } from "flowbite-react";

type SelectableCardProps = CardProps & {
  selected?: boolean;
  onSelect?: () => void;
  onDeselect?: () => void;
};

const selectedTheme: CustomFlowbiteTheme["card"] = {
  root: {
    base: "flex rounded-lg border border-primary-300 bg-primary-300 shadow-md dark:border-primary-500 dark:bg-primary-700",
    children: "flex h-full flex-col justify-center gap-4",
    horizontal: {
      off: "flex-col",
      on: "flex-col md:max-w-xl md:flex-row",
    },
    href: "hover:bg-gray-100 dark:hover:bg-gray-700",
  },
};

export const SelectableCard: FC<SelectableCardProps> = ({
  selected,
  onSelect,
  onDeselect,
  children,
  ...props
}) => {
  const [isSelected, setIsSelected] = useState(selected);

  const onClick = (shouldSelect: boolean) => {
    if (shouldSelect) {
      setIsSelected(true);
      onSelect?.();
    } else {
      setIsSelected(false);
      onDeselect?.();
    }
  };

  return (
    <SelectableCardContext.Provider
      value={{ selected: isSelected, setSelected: setIsSelected }}
    >
      <Card
        {...props}
        theme={isSelected ? selectedTheme : undefined}
        onClick={() => onClick(!isSelected)}
      >
        {children}
      </Card>
    </SelectableCardContext.Provider>
  );
};

interface CardContextProps {
  selected: boolean;
  setSelected: (selected: boolean) => void;
}

const SelectableCardContext = createContext<CardContextProps>({
  selected: false,
  setSelected: () => {},
});
