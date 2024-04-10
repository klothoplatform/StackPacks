import { Table } from "flowbite-react";
import type { FC, HTMLProps } from "react";
import classNames from "classnames";
import { TbArrowDown, TbArrowsSort, TbArrowUp } from "react-icons/tb";

interface SortableHeaderCellProps extends HTMLProps<HTMLTableCellElement> {
  id: string;
  sortedBy: string | null;
  updateSort: (sort: string) => void;
  sortDirection?: "asc" | "desc";
}

export const SortableHeaderCell: FC<SortableHeaderCellProps> = ({
  id,
  sortedBy,
  updateSort,
  sortDirection,
  children,
  ...props
}) => {
  return (
    <Table.HeadCell
      onClick={() => {
        updateSort(id);
      }}
      {...props}
    >
      <div
        className={classNames(
          "cursor-pointer flex h-full w-full items-center gap-2",
          {
            "[&>svg]:text-transparent [&>svg]:hover:text-gray-700 [&>svg]:dark:hover:text-gray-400":
              sortedBy !== id,
          },
        )}
      >
        <span>{children}</span>
        {sortedBy !== id && <TbArrowsSort />}
        {sortedBy === id && sortDirection === "asc" && <TbArrowUp />}
        {sortedBy === id && sortDirection === "desc" && <TbArrowDown />}
      </div>
    </Table.HeadCell>
  );
};
