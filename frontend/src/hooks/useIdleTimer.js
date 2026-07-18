import { useEffect, useRef } from "react";

const LAST_ACTIVE_KEY = "app_last_active";
const ACTIVITY_EVENTS = ["mousemove", "keydown", "click", "touchstart", "scroll"];

// Auto-logs out after `timeoutMs` of inactivity. The last-activity timestamp is
// kept in sessionStorage so a page refresh doesn't quietly reset an already-expired
// idle clock — expiry is checked against storage before the timer is (re)armed.
export function useIdleTimer(timeoutMs, onTimeout, enabled) {
  const onTimeoutRef = useRef(onTimeout);
  onTimeoutRef.current = onTimeout;

  useEffect(() => {
    if (!enabled) return;

    const last = Number(sessionStorage.getItem(LAST_ACTIVE_KEY)) || Date.now();
    if (Date.now() - last >= timeoutMs) {
      onTimeoutRef.current();
      return;
    }

    const markActive = () => sessionStorage.setItem(LAST_ACTIVE_KEY, String(Date.now()));
    markActive();

    let timer = setTimeout(() => onTimeoutRef.current(), timeoutMs);
    const resetTimer = () => {
      markActive();
      clearTimeout(timer);
      timer = setTimeout(() => onTimeoutRef.current(), timeoutMs);
    };

    ACTIVITY_EVENTS.forEach((evt) => window.addEventListener(evt, resetTimer, { passive: true }));
    return () => {
      clearTimeout(timer);
      ACTIVITY_EVENTS.forEach((evt) => window.removeEventListener(evt, resetTimer));
    };
  }, [enabled, timeoutMs]);
}
