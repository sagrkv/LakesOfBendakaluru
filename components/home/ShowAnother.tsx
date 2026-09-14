"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

/**
 * Asks the server for a new random lake without leaving the page.
 * All three labels share one grid cell, so the button never changes width.
 */
export default function ShowAnother({ current }: { current: string }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const online = () => setOffline(false);
    window.addEventListener("online", online);
    return () => window.removeEventListener("online", online);
  }, []);

  function showAnother() {
    if (pending) return;
    if (!navigator.onLine) {
      setOffline(true);
      return;
    }
    setOffline(false);
    startTransition(() => router.refresh());
  }

  const state = pending ? "pending" : offline ? "offline" : "idle";
  const label = (show: boolean) => `[grid-area:1/1] ${show ? "" : "invisible"}`;

  return (
    <>
      <button
        type="button"
        onClick={showAnother}
        aria-disabled={pending}
        className="slip grid px-[0.6em] pt-[0.35em] pb-[0.4em] font-serif italic text-[26px] leading-none transition-[translate,box-shadow] duration-[120ms] ease-settle not-aria-disabled:hover:-translate-x-px not-aria-disabled:hover:-translate-y-px not-aria-disabled:active:translate-x-px not-aria-disabled:active:translate-y-0.5 aria-disabled:cursor-progress"
      >
        <span className={label(state === "idle")}>Show me another</span>
        <span className={label(state === "pending")}>Finding a lake</span>
        <span className={label(state === "offline")}>Offline, try again</span>
      </button>
      <p className="sr-only" aria-live="polite">
        Showing {current}
      </p>
    </>
  );
}
