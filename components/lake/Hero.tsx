import type { CSSProperties } from "react";
import Link from "next/link";
import type { LakeRecord } from "@/lib/lake";
import { paperFor } from "@/lib/valleys";
import Cutout from "@/components/paper/Cutout";
import { pointFrame, sheetFrame, type Frame } from "./frame";
import { printedYears } from "./years/maps";

/** The satellite view that shows through a phone and a laptop crop of the same square image. */
function Ground({ frame }: { frame: Frame }) {
  const src = (px: number) => `${frame.url(px)} ${px}w`;
  return (
    <>
      {/* A static export from Esri in UTM 43N; next/image cannot resize it without remote config. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={frame.url(1600)}
        srcSet={[src(800), src(1600), src(2400)].join(", ")}
        sizes="(min-width: 768px) 100vw, 125vw"
        alt=""
        fetchPriority="high"
        className="absolute inset-0 size-full grayscale"
      />
      {/* Grey pushed 35% toward cream, so the paper is the only colour. */}
      <div className="absolute inset-0 bg-table/35" />
    </>
  );
}

function siteStatement(lake: LakeRecord): { label: string; text: string; gap: boolean } {
  const history = lake.history;
  if (history?.nowOccupiedBy) return { label: "On the site now", text: history.nowOccupiedBy, gap: false };
  if (history?.knownOnlyFromOldMap) {
    const year = printedYears(history).at(-1);
    return { label: "Known only from an old map", text: year ? `Drawn here in ${year}` : "Drawn here once", gap: false };
  }
  return { label: "No outline on record", text: "Only this point is known", gap: true };
}

export default function Hero({ lake, name }: { lake: LakeRecord; name: string }) {
  const point = lake.location?.point;
  const sheetView = sheetFrame(lake);
  const frame = sheetView ?? (point ? pointFrame(point) : undefined);
  const valley = lake.water?.valley;
  const statement = sheetView ? undefined : point ? siteStatement(lake) : undefined;
  const box = frame?.box;

  return (
    <div className="relative aspect-[4/5] overflow-hidden bg-well md:aspect-[5/2]">
      {frame && box ? (
        <div className="absolute top-1/2 left-1/2 aspect-square w-[125%] -translate-x-1/2 -translate-y-1/2 md:w-full">
          <Ground frame={frame} />
          {sheetView && lake.sheet ? (
            <Cutout
              sheet={lake.sheet}
              valley={valley}
              lands
              role="img"
              aria-label={`The outline of ${name}`}
              className="absolute"
              style={{
                left: `${box.left}%`,
                top: `${box.top}%`,
                width: `${box.width}%`,
                height: `${box.height}%`,
              }}
            />
          ) : (
            <span
              role="img"
              aria-label={`Where ${name} is`}
              className="lands sheet-shadow absolute top-1/2 left-1/2 size-7 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-table"
              style={{ background: paperFor(valley).sheet } as CSSProperties}
            />
          )}
        </div>
      ) : null}

      <Link
        href="/"
        className="slip absolute top-4 left-4 px-3 pt-1.5 pb-2 font-serif text-[28px] leading-none italic underline-offset-4 hover:underline md:top-6 md:left-10"
        style={{ "--tilt": "-1.2deg" } as CSSProperties}
      >
        Lakes of Bendakaluru
      </Link>

      {statement ? (
        <div
          className="slip pastes absolute bottom-4 left-4 max-w-[calc(100%-32px)] px-4 pt-3 pb-3.5 md:bottom-10 md:left-10 md:max-w-md"
          style={{ "--tilt": "1.1deg", "--delay": "660ms" } as CSSProperties}
        >
          <div className="label">{statement.label}</div>
          <div className={`mt-1 font-serif text-[26px] leading-none md:text-[36px] ${statement.gap ? "missing" : ""}`}>
            {statement.text}
          </div>
        </div>
      ) : null}

      {!frame ? (
        <div
          className="slip absolute bottom-4 left-4 px-4 pt-3 pb-3.5 md:bottom-10 md:left-10"
          style={{ "--tilt": "1.1deg" } as CSSProperties}
        >
          <div className="label">Where it is</div>
          <div className="missing mt-1 font-serif text-[26px] leading-none md:text-[36px]">No location on record</div>
        </div>
      ) : null}
    </div>
  );
}
