import { useEffect, useRef } from 'react';

export function useAutoRefresh(
  callback: () => void | Promise<void>,
  intervalSeconds: number = 60
) {
  const savedCallback = useRef(callback);

  // Update ref when callback changes
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Set up interval
  useEffect(() => {
    if (intervalSeconds <= 0) return;

    const tick = () => {
      savedCallback.current();
    };

    const id = setInterval(tick, intervalSeconds * 1000);
    return () => clearInterval(id);
  }, [intervalSeconds]);
}
