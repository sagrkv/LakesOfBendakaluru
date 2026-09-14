import Link from "next/link";
import { formatCount } from "@/lib/format";
import { joinList } from "@/components/lake/words";
import { SURVEY_YEAR } from "./filter";
import type { MissingLake } from "./types";

const count = (lakes: MissingLake[], test: (lake: MissingLake) => unknown) => lakes.filter(test).length;
const are = (n: number) => (n === 1 ? "is" : "are");
const have = (n: number) => (n === 1 ? "has" : "have");

/** The note beside the bars: what kinds of lake they are, and what is on record since the survey. Counts come from the data. */
export default function RecordNote({ lakes }: { lakes: MissingLake[] }) {
  const kunte = count(lakes, (lake) => lake.kind === "kunte");
  const katte = count(lakes, (lake) => lake.kind === "katte");
  const kere = count(lakes, (lake) => lake.kind === "kere");
  const inWards = count(lakes, (lake) => lake.ward);
  const onList = count(lakes, (lake) => lake.onList2024);
  const monitored = count(lakes, (lake) => lake.monitoringPage);
  const wet = count(lakes, (lake) => lake.waterSeen && lake.waterSeen > SURVEY_YEAR);

  const kinds = [
    kunte && `${formatCount(kunte)} ${are(kunte)} small ponds (kunte)`,
    katte && `${formatCount(katte)} ${are(katte)} medium tanks (katte)`,
    kere && `${formatCount(kere)} ${are(kere)} large tanks (kere)`,
  ].filter((part): part is string => Boolean(part));
  const since = [
    onList && `${formatCount(onList)} ${are(onList)} on the state's 2024 lake list`,
    monitored && `${formatCount(monitored)} ${have(monitored)} a page on the city's lake monitoring site`,
    wet && `satellites saw water at ${formatCount(wet)}`,
  ].filter((part): part is string => Boolean(part));

  return (
    <>
      <p>
        The 2018 survey gives each lake&rsquo;s taluk and its extent.
        {kinds.length > 0 && ` Of these lakes, ${joinList(kinds)}.`} {formatCount(inWards)} of them{" "}
        {inWards === 1 ? "sits" : "sit"} inside today&rsquo;s city wards.
      </p>
      <p>
        {since.length > 0
          ? `Since 2018, ${joinList(since)}. The rest have nothing newer on record.`
          : "None of them has anything on record since 2018."}
      </p>
      <p>
        Choose a bar to list only those lakes.{" "}
        <Link href="/sources" className="ink-link">
          See the sources
        </Link>
      </p>
    </>
  );
}
