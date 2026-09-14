import Slip from "@/components/paper/Slip";
import { formatAcres, formatCount, pitches } from "@/lib/format";

/** The headline, the three numbers, and the city as a sheet with a hole where each past lake was. */
export default function PastHero({
  total,
  acres,
  withoutExtent,
  holes,
  width,
  height,
}: {
  total: number;
  acres: number;
  withoutExtent: number;
  /** Lakes with a place on the sheet. */
  holes: number;
  width: number;
  height: number;
}) {
  return (
    <section className="page-x pt-10 md:pt-16 pb-16 md:pb-26">
      <div className="grid grid-cols-12 gap-x-6 gap-y-16 items-start">
        <div className="col-span-12 lg:col-span-5">
          <h1 className="font-serif text-[64px] md:text-[96px] leading-[0.86] text-balance">Once upon a kere</h1>
          <p className="mt-6 max-w-[34rem]">
            Kere is Kannada for lake. {formatCount(total)} lakes in and around Bengaluru are on record as gone. This is
            when each one went and what took its place, as far as the record says.
          </p>

          <div className="mt-10 flex flex-wrap items-start gap-4">
            <Slip label="Lakes gone" seed="past-count" order={0}>
              {formatCount(total)}
            </Slip>
            <Slip label="Water area gone" seed="past-acres" order={1}>
              {formatAcres(acres)} acres
            </Slip>
            <Slip label="The same as" seed="past-pitches" order={2}>
              {pitches(acres)}
            </Slip>
          </div>
          {withoutExtent > 0 && (
            <p className="mt-6 label missing max-w-[34rem]">
              {formatCount(withoutExtent)} of them have no extent on record, so the true area is larger.
            </p>
          )}
        </div>

        <figure className="col-span-12 lg:col-span-7 min-w-0">
          {/* Drawn by the data pipeline and fetched on its own, so its 2,700 shapes stay out of the page. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/data/past-sheet.svg"
            width={width}
            height={height}
            fetchPriority="high"
            alt={`A sheet of dark paper with ${formatCount(holes)} holes punched where lakes used to be.`}
            className="lands origin-center sheet-shadow relative left-1/2 block h-auto w-[720px] max-w-none -translate-x-1/2 md:left-0 md:w-full md:translate-x-0 lg:w-[calc(100%+40px)]"
          />
          <figcaption className="mt-6 label font-normal text-missing max-w-[34rem]">
            Each hole is a lake that is gone, punched where it was. Holes are drawn six times wider than the lakes
            were, so the small ones show. Faint dots are lakes that are still there.
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
