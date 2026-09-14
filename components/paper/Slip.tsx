import type { CSSProperties, ReactNode } from "react";

/** A stable tilt between -1.8 and 1.8 degrees, so server and browser agree. */
export function tiltFor(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  return ((Math.abs(hash) % 37) - 18) / 10;
}

/**
 * A cream slip pasted on top of a sheet or the table: a label, then the fact.
 * `order` staggers the paste-in by 60 ms per slip after the sheet lands.
 */
export default function Slip({
  label,
  children,
  seed,
  order,
  className = "",
}: {
  label: ReactNode;
  children: ReactNode;
  seed: string;
  order?: number;
  className?: string;
}) {
  const style = {
    "--tilt": `${tiltFor(seed)}deg`,
    "--delay": order === undefined ? undefined : `${600 + order * 60}ms`,
  } as CSSProperties;

  return (
    <div className={`slip px-4 pt-3 pb-3.5 ${order === undefined ? "" : "pastes"} ${className}`} style={style}>
      <div className="label">{label}</div>
      <div className="mt-1 font-serif text-[26px] md:text-[36px] leading-none">{children}</div>
    </div>
  );
}
