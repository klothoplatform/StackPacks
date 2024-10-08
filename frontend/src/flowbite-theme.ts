import type { CustomFlowbiteTheme } from "flowbite-react";

const flowbiteTheme: CustomFlowbiteTheme = {
  accordion: {
    root: {
      base: "divide-y divide-gray-200 border-gray-200 dark:divide-gray-700 dark:border-gray-700",
      flush: {
        off: "rounded-lg border",
        on: "border-b",
      },
    },
    content: {
      base: "p-5 first:rounded-t-lg last:rounded-b-lg dark:bg-gray-900",
    },
    title: {
      arrow: {
        base: "h-6 w-6 shrink-0",
        open: {
          off: "",
          on: "rotate-180",
        },
      },
      base: "flex w-full items-center justify-between p-5 text-left font-medium text-gray-500 first:rounded-t-lg last:rounded-b-lg dark:text-gray-400",
      flush: {
        off: "hover:bg-gray-100 focus:ring-4 focus:ring-gray-200 dark:hover:bg-gray-800 dark:focus:ring-gray-800",
        on: "bg-transparent dark:bg-transparent",
      },
      heading: "",
      open: {
        off: "last-of-type:rounded-b-lg",
        on: "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-white",
      },
    },
  },
  alert: {
    wrapper:
      "max-w-full flex items-center [&_div]:max-w-full [&_div]:overflow-hidden",
    color: {
      info: "text-cyan-800 border-cyan-300 rounded-lg bg-cyan-50 dark:bg-gray-800 dark:text-cyan-400 dark:border-cyan-800",
      failure:
        "text-red-800 border-red-300 rounded-lg bg-red-50 dark:bg-gray-800 dark:text-red-400 dark:border-red-800",
      success:
        "text-green-800 border-green-300 rounded-lg bg-green-50 dark:bg-gray-800 dark:text-green-400 dark:border-green-800",
      warning:
        "text-yellow-800 border-yellow-300 rounded-lg bg-yellow-50 dark:bg-gray-800 dark:text-yellow-400 dark:border-yellow-800",
      dark: "text-gray-800 border-gray-300 rounded-lg bg-gray-50 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600",
    },
    closeButton: {
      color: {
        info: "bg-cyan-50 text-cyan-500 rounded-lg focus:ring-2 focus:ring-cyan-400 hover:bg-cyan-200 dark:bg-gray-800 dark:text-cyan-400 dark:hover:bg-gray-700",
        failure:
          "bg-red-50 text-red-500 rounded-lg focus:ring-2 focus:ring-red-400 hover:bg-red-200 dark:bg-gray-800 dark:text-red-400 dark:hover:bg-gray-700",
        success:
          "bg-green-50 text-green-500 rounded-lg focus:ring-2 focus:ring-green-400 hover:bg-green-200 dark:bg-gray-800 dark:text-green-400 dark:hover:bg-gray-700",
        warning:
          "bg-yellow-50 text-yellow-500 rounded-lg focus:ring-2 focus:ring-yellow-400 hover:bg-yellow-200 dark:bg-gray-800 dark:text-yellow-400 dark:hover:bg-gray-700",
        dark: "bg-gray-50 text-gray-500 rounded-lg focus:ring-2 focus:ring-gray-400 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700",
      },
    },
  },
  button: {
    color: {
      purple:
        "text-white bg-primary-600 border border-transparent enabled:hover:bg-primary-700 focus:ring-4 focus:ring-primary-200 dark:bg-primary-700 dark:enabled:hover:bg-primary-600 dark:focus:ring-primary-800",
      dark: "text-white bg-gray-800 border border-transparent enabled:hover:bg-gray-900 focus:ring-4 focus:ring-gray-300 dark:bg-gray-800 dark:enabled:hover:bg-gray-700 dark:focus:ring-gray-800 dark:border-gray-700",
      failure:
        "text-white bg-red-700 border border-transparent enabled:hover:bg-red-800 focus:ring-4 focus:ring-red-300 dark:bg-red-600 dark:enabled:hover:bg-red-700 dark:focus:ring-red-900",
      gray: "text-gray-900 bg-white border border-gray-200 enabled:hover:bg-gray-100 enabled:hover:text-primary-700 :ring-primary-700 focus:text-primary-700 dark:bg-transparent dark:text-gray-400 dark:border-gray-600 dark:enabled:hover:text-white dark:enabled:hover:bg-gray-700 focus:ring-4",
      info: "text-white bg-primary-700 border border-transparent enabled:hover:bg-primary-800 focus:ring-4 focus:ring-primary-300 dark:bg-primary-600 dark:enabled:hover:bg-primary-700 dark:focus:ring-primary-800",
      light:
        "text-gray-900 bg-white border border-gray-300 enabled:hover:bg-gray-100 focus:ring-4 focus:ring-primary-300 dark:bg-gray-600 dark:text-white dark:border-gray-600 dark:enabled:hover:bg-gray-700 dark:enabled:hover:border-gray-700 dark:focus:ring-gray-700",
      success:
        "text-white bg-green-700 border border-transparent enabled:hover:bg-green-800 focus:ring-4 focus:ring-green-300 dark:bg-green-600 dark:enabled:hover:bg-green-700 dark:focus:ring-green-800",
      warning:
        "text-white bg-yellow-400 border border-transparent enabled:hover:bg-yellow-500 focus:ring-4 focus:ring-yellow-300 dark:focus:ring-yellow-900",
      blue: "text-white bg-blue-700 border border-transparent enabled:hover:bg-blue-800 focus:ring-4 focus:ring-blue-300 dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800",
      cyan: "text-cyan-900 bg-white border border-cyan-300 enabled:hover:bg-cyan-100 focus:ring-4 focus:ring-cyan-300 dark:bg-cyan-600 dark:text-white dark:border-cyan-600 dark:enabled:hover:bg-cyan-700 dark:enabled:hover:border-cyan-700 dark:focus:ring-cyan-700",
      green:
        "text-green-900 bg-white border border-green-300 enabled:hover:bg-green-100 focus:ring-4 focus:ring-green-300 dark:bg-green-600 dark:text-white dark:border-green-600 dark:enabled:hover:bg-green-700 dark:enabled:hover:border-green-700 dark:focus:ring-green-700",
      indigo:
        "text-indigo-900 bg-white border border-indigo-300 enabled:hover:bg-indigo-100 focus:ring-4 focus:ring-indigo-300 dark:bg-indigo-600 dark:text-white dark:border-indigo-600 dark:enabled:hover:bg-indigo-700 dark:enabled:hover:border-indigo-700 dark:focus:ring-indigo-700",
      lime: "text-lime-900 bg-white border border-lime-300 enabled:hover:bg-lime-100 focus:ring-4 focus:ring-lime-300 dark:bg-lime-600 dark:text-white dark:border-lime-600 dark:enabled:hover:bg-lime-700 dark:enabled:hover:border-lime-700 dark:focus:ring-lime-700",
      pink: "text-pink-900 bg-white border border-pink-300 enabled:hover:bg-pink-100 focus:ring-4 focus:ring-pink-300 dark:bg-pink-600 dark:text-white dark:border-pink-600 dark:enabled:hover:bg-pink-700 dark:enabled:hover:border-pink-700 dark:focus:ring-pink-700",
      red: "text-red-900 bg-white border border-red-300 enabled:hover:bg-red-100 focus:ring-4 focus:ring-red-300 dark:bg-red-600 dark:text-white dark:border-red-600 dark:enabled:hover:bg-red-700 dark:enabled:hover:border-red-700 dark:focus:ring-red-700",
      teal: "text-teal-900 bg-white border border-teal-300 enabled:hover:bg-teal-100 focus:ring-4 focus:ring-teal-300 dark:bg-teal-600 dark:text-white dark:border-teal-600 dark:enabled:hover:bg-teal-700 dark:enabled:hover:border-teal-700 dark:focus:ring-teal-700",
      yellow:
        "text-yellow-900 bg-white border border-yellow-300 enabled:hover:bg-yellow-100 focus:ring-4 focus:ring-yellow-300 dark:bg-yellow-600 dark:text-white dark:border-yellow-600 dark:enabled:hover:bg-yellow-700 dark:enabled:hover:border-yellow-700 dark:focus:ring-yellow-700",
    },
    inner: {
      base: "flex items-center transition-all duration-200",
    },
    outline: {
      color: {
        gray: "border border-gray-200 dark:border-gray-500",
        purple: "border-0 border-primary-600 [&>*]:hover:text-white",
      },
    },
  },
  card: {
    root: {
      children: "flex size-full flex-col justify-center gap-4",
    },
  },
  checkbox: {
    root: {
      color: {
        default:
          "focus:ring-primary-600 dark:ring-offset-primary-600 dark:focus:ring-primary-600 text-primary-600 dark:focus:border-white",
      },
    },
  },
  dropdown: {
    arrowIcon: "ml-2 h-4 w-4",
    content: "py-1 focus:outline-none",
    floating: {
      animation: "transition-opacity",
      arrow: {
        base: "absolute z-10 h-2 w-2 rotate-45",
        style: {
          dark: "bg-gray-900 dark:bg-gray-700",
          light: "bg-white",
          auto: "bg-white dark:bg-gray-700",
        },
        placement: "-4px",
      },
      base: "z-10 w-fit divide-y divide-gray-100 rounded shadow focus:outline-none",
      content: "py-1 text-sm text-gray-700 dark:text-gray-200",
      divider: "my-1 h-px bg-gray-100 dark:bg-gray-600",
      header: "block px-4 py-2 text-sm text-gray-700 dark:text-gray-200",
      hidden: "invisible opacity-0",
      item: {
        container: "",
        base: "flex w-full cursor-pointer items-center justify-start px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 focus:bg-gray-100 focus:outline-none dark:text-gray-200 dark:hover:bg-gray-600 dark:hover:text-white dark:focus:bg-gray-600 dark:focus:text-white disabled:text-gray-400 disabled:dark:text-gray-500 disabled:italic",
        icon: "mr-2 h-4 w-4",
      },
      style: {
        dark: "bg-gray-900 text-white dark:bg-gray-700",
        light: "border border-gray-200 bg-white text-gray-900",
        auto: "border border-gray-200 bg-white text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white",
      },
      target: "w-fit",
    },
    inlineWrapper: "flex items-center",
  },
  modal: {
    content: {
      inner: "relative rounded-lg bg-white shadow dark:bg-gray-800",
    },
    header: {
      base: "flex items-start justify-between rounded-t px-5 pt-5",
    },
  },
  navbar: {
    root: {
      base: "relative z-1 w-full bg-white border-b border-gray-200 dark:bg-gray-800 dark:border-gray-700",
    },
  },
  sidebar: {
    root: {
      base: "flex relative top-0 z-20 flex-col flex-shrink-0 h-full duration-75 border-r border-gray-200 lg:flex transition-width dark:border-gray-700",
      inner:
        "h-full overflow-y-auto overflow-x-hidden rounded bg-gray-50 p-4 dark:bg-gray-800",
    },
    item: {
      base: "flex items-center justify-center rounded-lg p-2 text-base font-medium text-gray-900 hover:bg-gray-100 dark:text-white dark:hover:bg-gray-700 cursor-pointer",
      collapsed: {
        insideCollapse: "group w-full pl-8 transition duration-75",
        noIcon: "font-bold",
      },
      content: {
        base: "flex-1 px-3 whitespace-nowrap",
      },
      icon: {
        base: "h-6 w-6 flex-shrink-0 text-gray-500 transition duration-75 group-hover:text-gray-900 dark:text-gray-400 dark:group-hover:text-white",
        active: "text-gray-700 dark:text-gray-100",
      },
      active:
        "bg-gray-100 dark:bg-gray-700 pr-2 pl-0 before:relative before:-left-2 before:mr-1 before:h-6 before:content-[' '] before:inline-block before:bg-primary-600 dark:before:bg-primary-500 before:w-1 before:rounded-lg before:ps-0.5 before:pe-0.5",
    },
    collapse: {
      button:
        "group flex w-full items-center rounded-lg p-2 text-base font-medium text-gray-900 transition duration-75 hover:bg-gray-100 dark:text-white dark:hover:bg-gray-700",
    },
  },
  textarea: {
    base: "block w-full text-sm p-4 rounded-lg border disabled:cursor-not-allowed disabled:opacity-50",
  },
  helperText: {
    root: {
      colors: {
        purple: "text-purple-600 dark:text-purple-500",
        gray: "text-gray-500 dark:text-gray-400",
        info: "text-cyan-600 dark:text-cyan-500",
        success: "text-green-600 dark:text-green-500",
        failure: "text-red-600 dark:text-red-500",
        warning: "text-yellow-600 dark:text-yellow-500",
      },
    },
  },
  textInput: {
    field: {
      base: "relative w-full",
      input: {
        base: "block w-full border disabled:cursor-not-allowed disabled:opacity-50 text-green-500",
        colors: {
          success:
            "focus:outline-none focus:ring-1 bg-green-50 border-green-500 text-green-900 dark:text-green-400 placeholder-green-700 dark:placeholder-green-500 focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:border-green-500",
          failure:
            "focus:outline-none focus:ring-1 bg-red-50 border-red-500 text-red-900 placeholder-red-700 focus:ring-red-500 dark:bg-gray-700 focus:border-red-500 dark:text-red-500 dark:placeholder-red-500 dark:border-red-500",
          warning:
            "focus:outline-none focus:ring-1 bg-yellow-50 border-yellow-500 text-yellow-900 placeholder-yellow-700 focus:ring-yellow-500 dark:bg-gray-700 focus:border-yellow-500 dark:text-yellow-500 dark:placeholder-yellow-500 dark:border-yellow-500",
          info: "focus:outline-none focus:ring-1 bg-blue-50 border-blue-500 text-blue-900 placeholder-blue-700 focus:ring-blue-500 dark:bg-gray-700 focus:border-blue-500 dark:text-blue-500 dark:placeholder-blue-500 dark:border-blue-500",
          gray: "bg-gray-50 border-gray-300 text-gray-900 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500",
          purple:
            "focus:outline-none focus:ring-1 bg-purple-50 border-purple-500 text-purple-900 placeholder-purple-700 focus:ring-purple-500 dark:bg-gray-700 focus:border-purple-500 dark:text-purple-500 dark:placeholder-purple-500 dark:border-purple-500",
        },
      },
    },
  },
  toggleSwitch: {
    toggle: {
      checked: {
        color: {
          blue: "bg-blue-700 border-blue-700",
        },
      },
    },
  },
  tooltip: {
    // max-w-max is required to avoid tooltip causing ResizeObserver loop limit exceeded error
    base: "absolute inline-block z-10 rounded-lg py-2 px-3 text-sm font-medium shadow-sm max-w-max w-fit",
    content: "relative z-20 max-w-max w-max",
    target: "",
  },
  table: {
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
      base: "group/head text-xs text-gray-700 dark:text-gray-400 border-b",
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
  },
};
export default flowbiteTheme;
