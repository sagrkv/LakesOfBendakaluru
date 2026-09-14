import Slip from "@/components/paper/Slip";
import SourceLink from "@/components/paper/SourceLink";
import { formatAcres, formatCount, pitches } from "@/lib/format";
import { getSource } from "@/lib/lakes";
import { getPunchedCity, type LostLake } from "./lost";
import PunchedSheet from "./PunchedSheet";

export default function ForgottenHero({
  lost,
  acres,
  withoutExtent,
}: {
  lost: LostLake[];
  acres: number;
  withoutExtent: number;
}) {
  const city = getPunchedCity(lost);

  return (
    <section className="page-x pt-10 md:pt-16 pb-16 md:pb-26">
      <div className="grid grid-cols-12 gap-x-6 gap-y-16 items-start">
        <div className="col-span-12 lg:col-span-5">
          <h1 className="font-serif text-[64px] md:text-[96px] leading-[0.86] text-balance">
            Forgotten lakes of Bendakaluru
          </h1>
          <p className="mt-6 max-w-[34rem]">
            These lakes are on record as gone. What is left of each is a point on the map, the extent on record and a
            note of what stands on the site now.
          </p>
          <SourceLink source={getSource("empri-2018")} className="mt-2 inline-block" />

          <div className="mt-10 flex flex-wrap items-start gap-4">
            <Slip label="Lakes gone" seed="forgotten-count" order={0}>
              {formatCount(lost.length)}
            </Slip>
            <Slip label="Water area gone" seed="forgotten-acres" order={1}>
              {formatAcres(acres)} acres
            </Slip>
            <Slip label="The same as" seed="forgotten-pitches" order={2}>
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
          <PunchedSheet
            id="forgotten-city"
            width={city.width}
            height={city.height}
            holes={city.holes}
            dots={city.dots}
            label={`A sheet of dark paper with ${formatCount(city.holes.length)} holes punched where lakes used to be.`}
            className="relative left-1/2 w-[720px] max-w-none -translate-x-1/2 md:left-0 md:w-full md:translate-x-0 lg:w-[calc(100%+40px)]"
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
