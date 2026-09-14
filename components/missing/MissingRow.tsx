import Link from "next/link";
import { formatAcres } from "@/lib/format";
import { SURVEY_YEAR, type Tagged } from "./filter";
import { kindLine, mapLine, placeLine, surveyLine, waterLine } from "./words";

export const ROW = "-mx-2 px-2 grid-cols-12 gap-x-6 items-baseline";
const SMALL = "label font-normal md:text-[17px] md:leading-[1.55]";

/**
 * One missing lake: its name, the 2018 extent, where it is and who looks after it, and what the record says,
 * old and new. The whole row opens the lake's page; the monitoring site link sits above that.
 */
export default function MissingRow({ lake, printed }: { lake: Tagged; printed?: number[] }) {
  const kind = kindLine(lake.kind);
  const place = placeLine(lake);
  const survey = surveyLine(lake);
  const maps = mapLine(lake.onMap, printed);
  const water = waterLine(lake.waterSeen);
  const waterIsNewer = Boolean(lake.waterSeen && lake.waterSeen > SURVEY_YEAR);

  return (
    <li className="border-b border-rule [content-visibility:auto] [contain-intrinsic-size:auto_152px] md:[contain-intrinsic-size:auto_112px]">
      <div className={`${ROW} relative grid gap-y-1 py-3 hover:bg-well active:bg-rule`}>
        <div className="col-span-8 md:col-span-3 min-w-0">
          <Link
            href={`/lake/${lake.id}`}
            prefetch={false}
            className="ink-link after:absolute after:inset-0 after:content-['']"
          >
            {lake.name}
          </Link>
          {lake.nameKannada && (
            <span lang="kn" className="mt-1 block font-kannada font-semibold label leading-[1.6]">
              {lake.nameKannada}
            </span>
          )}
          {kind && <span className="mt-1 block label font-normal">{kind}</span>}
        </div>

        <span className="col-span-4 md:col-span-2 text-right tabular-nums">
          {lake.acres ? (
            <>
              {formatAcres(lake.acres)}
              <span className="md:sr-only"> acres</span>
            </>
          ) : (
            <span className="missing">not recorded</span>
          )}
        </span>

        <div className={`col-span-12 md:col-span-3 ${SMALL}`}>
          <span className="sr-only">Where: </span>
          {place ? <span className="block">{place}</span> : <span className="block missing">No village on record</span>}
          {lake.ward && <span className="block">{lake.ward} ward</span>}
          {lake.custodian ? (
            <span className="block">Looked after by {lake.custodian}</span>
          ) : (
            <span className="block missing">Nobody on record looks after it</span>
          )}
        </div>

        <div className={`col-span-12 md:col-span-4 ${SMALL}`}>
          <span className="sr-only">What the record says: </span>
          {survey && <span className="block">{survey}</span>}
          {maps && <span className="block">{maps}</span>}
          {water && !waterIsNewer && <span className="block">{water}</span>}
          {lake.onList2024 && <span className="block">On the state&rsquo;s 2024 lake list</span>}
          {lake.monitoringPage && (
            <a
              href={lake.monitoringPage}
              target="_blank"
              rel="noreferrer noopener"
              className="relative block w-fit ink-link"
            >
              Has a page on the city&rsquo;s lake monitoring site
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          )}
          {water && waterIsNewer && <span className="block">{water}</span>}
          {lake.newer === "none" && <span className="block missing">Nothing on record since the 2018 survey</span>}
        </div>
      </div>
    </li>
  );
}
