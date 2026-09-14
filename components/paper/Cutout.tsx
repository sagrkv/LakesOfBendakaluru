import type { SVGProps } from "react";
import type { Sheet } from "@/lib/lake";
import { paperFor } from "@/lib/valleys";

/**
 * A lake cut from its valley's paper at its real outline. The SVG's user units are metres,
 * so anything drawn inside (the name, the span) shares the outline's scale.
 */
export default function Cutout({
  sheet,
  valley,
  lands = false,
  children,
  ...svg
}: {
  sheet: Sheet;
  valley?: string;
  lands?: boolean;
} & Omit<SVGProps<SVGSVGElement>, "viewBox">) {
  const paper = paperFor(valley);
  // The shadow sits on the svg box, in screen pixels, so it looks the same whatever the lake's scale.
  return (
    <svg
      viewBox={`0 0 ${sheet.w} ${sheet.h}`}
      overflow="visible"
      {...svg}
      className={`${lands ? "lands" : "sheet-shadow"} ${svg.className ?? ""}`}
    >
      <path d={sheet.d} fill={paper.sheet} fillRule="evenodd" />
      {children}
    </svg>
  );
}
