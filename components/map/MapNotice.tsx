import type { CSSProperties, ReactNode } from "react";

/** A slip on the map for loading, failure and "cannot draw" states. Loading waits 400 ms so fast loads never flash it. */
export default function MapNotice({
  children,
  action,
  delayed = false,
}: {
  children: ReactNode;
  action?: { label: string; onClick: () => void };
  delayed?: boolean;
}) {
  return (
    <div
      role="status"
      className={`slip pointer-events-auto w-full max-w-[380px] px-4 py-3 ${delayed ? "pastes" : ""}`}
      style={delayed ? ({ "--delay": "400ms" } as CSSProperties) : undefined}
    >
      <p className="text-[17px]">{children}</p>
      {action ? (
        <button type="button" onClick={action.onClick} className="button-ink mt-3 text-[28px]">
          {action.label}
        </button>
      ) : null}
    </div>
  );
}
