import type { CSSProperties, ReactNode } from "react";
import type { Source } from "@/lib/lake";
import { tiltFor } from "@/components/paper/Slip";
import SourceLink from "@/components/paper/SourceLink";

/**
 * One field of a lake page: a cream slip with a label, the fact, and where it comes from.
 * Wide slips hold charts and tables, so they tilt a third as much and stay readable.
 */
export default function Fact({
  label,
  value,
  children,
  sources = [],
  wide = false,
}: {
  label: string;
  value?: ReactNode;
  children?: ReactNode;
  sources?: Source[];
  wide?: boolean;
}) {
  const tilt = tiltFor(label) * (wide ? 0.33 : 1);
  return (
    <div
      className={`slip min-w-0 px-4 pt-3 pb-4 ${wide ? "sm:col-span-2 xl:col-span-3" : ""}`}
      style={{ "--tilt": `${tilt}deg` } as CSSProperties}
    >
      <div className="label">{label}</div>
      {value !== undefined ? (
        <div className="mt-1 font-serif text-[26px] md:text-[36px] leading-none break-words">{value}</div>
      ) : null}
      {children !== undefined ? <div className={value !== undefined ? "mt-2" : "mt-1"}>{children}</div> : null}
      {sources.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
          {sources.map((source) => (
            <SourceLink key={source.key} source={source} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/** A qualifier under a fact's value. */
export function Note({ children }: { children: ReactNode }) {
  return <p className="label font-normal">{children}</p>;
}
