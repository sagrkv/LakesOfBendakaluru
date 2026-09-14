import Slip, { tiltFor } from "@/components/paper/Slip";
import { formatAcres, formatCount } from "@/lib/format";
import type { CSSProperties } from "react";

/** The headline, the three numbers, and the city as dots with a ring at each lake no map draws. */
export default function MissingHero({
  total,
  median,
  newer,
  withoutExtent,
  width,
  height,
}: {
  total: number;
  /** Half the lakes are smaller than this, in acres. */
  median: number;
  /** Lakes with anything on record since 2018. */
  newer: number;
  withoutExtent: number;
  width: number;
  height: number;
}) {
  // Pasted after the three number slips, 60 ms apart like them.
  const tilt = { "--tilt": `${tiltFor("missing-locator")}deg`, "--delay": "780ms" } as CSSProperties;

  return (
    <section className="page-x pt-10 md:pt-16 pb-16 md:pb-26">
      <div className="grid grid-cols-12 gap-x-6 gap-y-16 items-start">
        <div className="col-span-12 lg:col-span-5">
          <h1 className="font-serif text-[64px] md:text-[96px] leading-[0.86] text-balance">Missing lakes of Bangalore</h1>
          <p className="mt-6 max-w-[34rem]">
            In 2018 the state&rsquo;s lake survey recorded {formatCount(total)} lakes in and around Bengaluru as still
            there. No map we have draws them, so they are not on our map. Most are small ponds, and half are under{" "}
            {formatAcres(median)} acres. The record does not say whether each one is still there. This is what it does
            say.
          </p>

          <div className="mt-10 flex flex-wrap items-start gap-4">
            <Slip label="Lakes no map draws" seed="missing-count" order={0}>
              {formatCount(total)}
            </Slip>
            <Slip label="Half are under" seed="missing-median" order={1}>
              {formatAcres(median)} acres
            </Slip>
            <Slip label="On record since 2018" seed="missing-newer" order={2}>
              {formatCount(newer)} of {formatCount(total)}
            </Slip>
          </div>
          {withoutExtent > 0 && (
            <p className="mt-6 label missing max-w-[34rem]">
              {formatCount(withoutExtent)} of them have no extent on record, so they are left out of the size.
            </p>
          )}
        </div>

        <figure className="col-span-12 lg:col-span-7 min-w-0">
          <div className="slip pastes p-4 md:p-6" style={tilt}>
            {/* Drawn by the data pipeline and fetched on its own, so its 1,600 dots stay out of the page. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/data/missing-sheet.svg"
              width={width}
              height={height}
              fetchPriority="high"
              alt={`Bengaluru's lakes drawn as dots, with a ring at each of the ${formatCount(total)} lakes no map draws.`}
              className="block h-auto w-full"
            />
          </div>
          <figcaption className="mt-6 label font-normal text-missing max-w-[34rem]">
            Each ring is a lake no map draws, placed where the 2018 survey put it. Faint dots are the lakes a map does
            draw.
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
