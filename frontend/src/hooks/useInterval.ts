import { useEffect, useRef } from "react";

/**
 * Custom hook to use setInterval in functional components
 *
 * @see https://overreacted.io/making-setinterval-declarative-with-react-hooks/
 *
 * @param callback function to call at each interval
 * @param delay time in milliseconds to wait between each call - if null, the interval is cleared and the callback is not called until the delay is set again
 */
export function useInterval(callback: Function, delay: number | null) {
  const savedCallback = useRef<Function>();

  // Remember the latest callback.
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Set up the interval.
  useEffect(() => {
    function tick() {
      savedCallback.current?.();
    }
    if (delay !== null) {
      let id = setInterval(tick, delay);
      return () => clearInterval(id);
    }
  }, [delay]);
}
