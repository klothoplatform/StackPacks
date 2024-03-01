import { useEffect, useRef } from "react";
import { useEffectOnMount } from "./useEffectOnMount.ts";

export function useDocumentTitle(title: string, prevailOnUnmount = false) {
  const defaultTitle = useRef(document.title);

  useEffect(() => {
    document.title = title;
  }, [title]);

  useEffectOnMount(() => () => {
    if (!prevailOnUnmount) {
      document.title = defaultTitle.current;
    }
  });
}
