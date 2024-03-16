import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

export function useScrollToAnchor(options: {
  behavior: ScrollBehavior;
  mode: "auto" | "always";
}) {
  const mode = options.mode || "auto";
  const behavior = options.behavior || "smooth";
  const location = useLocation();
  const lastHash = useRef("");

  // listen to location change using useEffect with location as dependency
  // https://jasonwatmore.com/react-router-v6-listen-to-location-route-change-without-history-listen
  useEffect(() => {
    if (location.hash) {
      lastHash.current = location.hash.slice(1); // save hash for further use after navigation
    }

    const element = document.getElementById(lastHash.current);
    if (
      lastHash.current &&
      element &&
      (mode !== "auto" || !isScrolledIntoView(element))
    ) {
      setTimeout(() => {
        document
          .getElementById(lastHash.current)
          ?.scrollIntoView({ behavior: behavior, block: "start" });
        lastHash.current = "";
      }, 100);
    }
  }, [location, mode, behavior]);
}

function isScrolledIntoView(elem: HTMLElement): boolean {
  const docViewTop = window.scrollY;
  const docViewBottom = docViewTop + window.innerHeight;

  const elemRect = elem.getBoundingClientRect();
  const elemTop = elemRect.top + docViewTop;
  const elemBottom = elemTop + elemRect.height;

  return elemBottom <= docViewBottom && elemTop >= docViewTop;
}
