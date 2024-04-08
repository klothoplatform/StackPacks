/*
    Reusable non-default flowbite component themes can be defined here.
 */

import type { CustomFlowbiteTheme } from "flowbite-react";

export const OutlinedAlert: CustomFlowbiteTheme["alert"] = {
  wrapper:
    "max-w-full flex items-center [&_div]:max-w-full [&_div]:overflow-hidden",
  color: {
    info: "text-cyan-800 border border-cyan-300 rounded-lg bg-cyan-50 dark:bg-gray-800 dark:text-cyan-400 dark:border-cyan-800",
    failure:
      "text-red-800 border border-red-300 rounded-lg bg-red-50 dark:bg-gray-800 dark:text-red-400 dark:border-red-800",
    success:
      "text-green-800 border border-green-300 rounded-lg bg-green-50 dark:bg-gray-800 dark:text-green-400 dark:border-green-800",
    warning:
      "text-yellow-800 border border-yellow-300 rounded-lg bg-yellow-50 dark:bg-gray-800 dark:text-yellow-400 dark:border-yellow-800",
    dark: "text-gray-800 border border-gray-300 rounded-lg bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600",
  },
};

export const outlineBadge: CustomFlowbiteTheme["badge"] = {
  root: {
    color: {
      success:
        "text-green-800 bg-green-100 dark:bg-green-700/20 dark:text-green-400 border border-green-400",
      warning:
        "text-yellow-800 bg-yellow-100 dark:bg-yellow-700/20 dark:text-yellow-300 border border-yellow-300",
      failure:
        "text-red-800 bg-red-100 dark:bg-red-700/20 dark:text-red-400 border border-red-400",
      info: "text-cyan-800 bg-cyan-100 dark:bg-cyan-700/20 dark:text-cyan-400 border border-cyan-400",
      dark: "text-gray-800 bg-gray-100 dark:bg-gray-700/20 dark:text-gray-300 border border-gray-600",
      light:
        "text-gray-800 bg-gray-100 dark:bg-gray-700/20 dark:text-gray-400 border border-gray-500",
      blue: "text-blue-800 bg-blue-100 dark:bg-blue-700/20 dark:text-blue-400 border border-blue-400",
      indigo:
        "text-indigo-800 bg-indigo-100 dark:bg-indigo-700/20 dark:text-indigo-400 border border-indigo-400",
      purple:
        "text-purple-800 bg-purple-100 dark:bg-purple-700/20 dark:text-purple-400 border border-purple-400",
      pink: "text-pink-800 bg-pink-100 dark:bg-pink-700/20 dark:text-pink-400 border border-pink-400",
      yellow:
        "text-yellow-800 bg-yellow-100 dark:bg-yellow-700/20 dark:text-yellow-300 border border-yellow-300",
      green:
        "text-green-800 bg-green-100 dark:bg-green-700/20 dark:text-green-400 border border-green-400",
      red: "text-red-800 bg-red-100 dark:bg-red-700/20 dark:text-red-400 border border-red-400",
      cyan: "text-cyan-800 bg-cyan-100 dark:bg-cyan-700/20 dark:text-cyan-400 border border-cyan-400",
      gray: "text-gray-800 bg-gray-100 dark:bg-gray-700/20 dark:text-gray-300 border border-gray-600",
      teal: "text-teal-800 bg-teal-100 dark:bg-teal-700/20 dark:text-teal-400 border border-teal-400",
    },
  },
};

export const outlineOnlyBadge: CustomFlowbiteTheme["badge"] = {
  root: {
    color: {
      success: "text-green-800 dark:text-green-400 border border-green-400",
      warning: "text-yellow-800 dark:text-yellow-300 border border-yellow-300",
      failure: "text-red-800 dark:text-red-400 border border-red-400",
      info: "text-cyan-800 dark:text-cyan-400 border border-cyan-400",
      dark: "text-gray-800 dark:text-gray-300 border border-gray-600",
      light: "text-gray-800 dark:text-gray-400 border border-gray-500",
      blue: "text-blue-800 dark:text-blue-400 border border-blue-400",
      indigo: "text-indigo-800 dark:text-indigo-400 border border-indigo-400",
      purple: "text-purple-800 dark:text-purple-400 border border-purple-400",
      pink: "text-pink-800 dark:text-pink-400 border border-pink-400",
      yellow: "text-yellow-800 dark:text-yellow-300 border border-yellow-300",
      green: "text-green-800 dark:text-green-400 border border-green-400",
      red: "text-red-800 dark:text-red-400 border border-red-400",
      cyan: "text-cyan-800 dark:text-cyan-400 border border-cyan-400",
      gray: "text-gray-800 dark:text-gray-300 border border-gray-600",
      teal: "text-teal-800 dark:text-teal-400 border border-teal-400",
    },
  },
};

export const altTable: CustomFlowbiteTheme["table"] = {
  root: {
    base: "w-full text-left text-sm text-gray-500 dark:text-gray-400 border-separate border-spacing-0",
    shadow:
      "absolute left-0 top-0 -z-10 h-full w-full rounded-lg bg-white drop-shadow-md dark:bg-black",
    wrapper: "relative",
  },
  body: {
    base: "group/body",
    cell: {
      base: "px-6 py-4 group-first/body:group-first/row:first:rounded-tl-lg group-first/body:group-first/row:last:rounded-tr-lg group-last/body:group-last/row:first:rounded-bl-lg group-last/body:group-last/row:last:rounded-br-lg group-last/body:group-last/row:border-b",
    },
  },
  head: {
    base: "group/head text-xs text-gray-700 dark:text-gray-400",
    cell: {
      base: "bg-gray-100 px-6 py-3 group-first/head:first:rounded-tl-lg group-first/head:last:rounded-tr-lg dark:bg-gray-800 border-t group-first/head:first:border-l group-first/head:last:border-r group-first/head:first:border-tl-rounded-lg border-gray-200 dark:border-gray-700",
    },
  },
  row: {
    base: "group/row odd:dark:bg-gray-900 even:dark:bg-gray-900 [&>*:first-child]:border-l [&>*:last-child]:border-r [&>*]:border-gray-200 [&>*]:dark:border-gray-700 [&>*]:border-t",
    hovered: "hover:bg-gray-50 dark:hover:bg-gray-600",
    striped:
      "odd:bg-gray-50 even:bg-gray-50 odd:dark:bg-gray-800 even:dark:bg-gray-700",
  },
};

export const flatTable: CustomFlowbiteTheme["table"] = {
  root: {
    base: "w-full text-left text-sm text-gray-800 dark:text-white",
    shadow:
      "absolute left-0 top-0 -z-10 h-full w-full bg-white drop-shadow-md dark:bg-black",
    wrapper: "relative",
  },
  body: {
    base: "group/body divide-y divide-gray-200 dark:divide-gray-700",
    cell: {
      base: "px-6 py-4",
    },
  },
  head: {
    base: "group/head text-sm text-gray-700 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700",
    cell: {
      base: "px-6 py-2",
    },
  },
  row: {
    base: "group/row dark:bg-gray-900",
    hovered: "hover:bg-gray-50 dark:hover:bg-gray-600",
    striped:
      "odd:bg-white even:bg-gray-100 odd:dark:bg-gray-800 even:dark:bg-gray-700",
  },
};
