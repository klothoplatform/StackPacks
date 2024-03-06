import type { RefObject } from "react";
import { useEffect } from "react";

/**
 * Hook that executes a callback when clicked outside of the passed ref
 *
 * @param ref - The ref to the element
 * @param callback - The callback to execute
 * @returns void
 *
 * @example
 * ```tsx
 * const ref = useRef(null);
 * useClickedOutside(ref, () => console.log("Clicked outside"));
 *
 * return <div ref={ref}>Click outside</div>
 * ```
 */

export function useClickedOutside<T extends HTMLElement>(
  ref: RefObject<T>,
  callback: () => void,
) {
  useEffect(() => {
    /**
     * Alert if clicked on outside of element
     */
    function handleClickOutside(event) {
      if (!ref.current || !ref.current.contains(event.target)) {
        callback();
      }
    }
    // Bind the event listener
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      // Unbind the event listener on clean up
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [callback, ref]);
}
