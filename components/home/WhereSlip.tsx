import type { CSSProperties } from "react";
import { tiltFor } from "@/components/paper/Slip";
import type { LakeRecord, Sheet } from "@/lib/lake";
import { formatCoords, formatMetres } from "@/lib/format";
import { ROOM_PX, ROOM_PX_PHONE } from "./fit";
import Locator from "./Locator";
import type { City } from "./opener";

/** The longest round length (1, 2 or 5 times a power of ten, in metres) that fits in `maxPx`. */
function scaleBar(pxPerMetre: number, maxPx: number): { metres: number; px: number } {
  let best = { metres: 1, px: pxPerMetre };
  for (let power = 1; power <= 100000; power *= 10) {
    for (const step of [1, 2, 5]) {
      const metres = step * power;
      if (metres * pxPerMetre <= maxPx) best = { metres, px: metres * pxPerMetre };
    }
  }
  return best;
}

function ScaleBar({ bar, className }: { bar: { metres: number; px: number }; className: string }) {
  return (
    <div className={`items-center gap-2 ${className}`}>
      <span
        aria-hidden="true"
        className="h-2 border-x-2 border-ink bg-[linear-gradient(var(--color-ink),var(--color-ink))] bg-[length:100%_2px] bg-center bg-no-repeat"
        style={{ width: bar.px }}
      />
      <span className="label tabular-nums">
        <span className="sr-only">Scale bar: </span>
        {formatMetres(bar.metres)}
      </span>
    </div>
  );
}

/** Where the lake is: the locator, its ward, coordinates, the drawing's scale and its end-to-end length. */
export default function WhereSlip({
  lake,
  sheet,
  xy,
  city,
  sheetColor,
  order,
  className = "",
}: {
  lake: LakeRecord;
  sheet: Sheet;
  xy?: [number, number];
  city: City;
  sheetColor: string;
  order: number;
  className?: string;
}) {
  const ward = lake.location?.ward;
  const point = lake.location?.point;
  const style = { "--tilt": `${tiltFor(`${lake.id}-where`)}deg`, "--delay": `${600 + order * 60}ms` } as CSSProperties;

  return (
    <div className={`slip pastes px-4 pt-3 pb-4 ${className}`} style={style}>
      <div className="label">Where it is</div>
      <div className="mt-3 flex items-start gap-4">
        <Locator city={city} xy={xy} name={lake.name} sheetColor={sheetColor} className="w-[120px] shrink-0 md:w-[160px]" />
        <div className="min-w-0 [overflow-wrap:anywhere]">
          {ward?.name ? (
            <>
              <p className="font-serif text-[26px] leading-none md:text-[36px]">{ward.name} ward</p>
              {ward.corporation ? <p className="label mt-1">{ward.corporation}</p> : null}
            </>
          ) : (
            <p className="missing font-serif text-[26px] leading-none md:text-[36px]">
              {lake.location?.insideCity === false ? "Outside the city wards" : "No ward on record"}
            </p>
          )}
          {point ? <p className="label mt-4 tabular-nums">{formatCoords(point)}</p> : null}
          <ScaleBar bar={scaleBar(ROOM_PX_PHONE / sheet.room.w, 96)} className="mt-4 flex md:hidden" />
          <ScaleBar bar={scaleBar(ROOM_PX / sheet.room.w, 120)} className="mt-4 hidden md:flex" />
          <p className="mt-2 flex items-center gap-2">
            <svg aria-hidden="true" width="24" height="8" viewBox="0 0 24 8" className="shrink-0 fill-ink">
              <circle cx="3" cy="4" r="3" />
              <circle cx="12" cy="4" r="1.5" />
              <circle cx="21" cy="4" r="3" />
            </svg>
            <span className="label tabular-nums">{formatMetres(sheet.span.m)} end to end</span>
          </p>
        </div>
      </div>
    </div>
  );
}
