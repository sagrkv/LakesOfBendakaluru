import { formatAcres, formatCount } from "@/lib/format";
import { getLakes } from "@/lib/lakes";
import { SITE_NAME, SITE_URL } from "@/lib/share";

export const dynamic = "force-static";

/** How many of the largest standing lakes are listed by name, so an assistant can link the ones people ask about most. */
const LISTED = 100;

/** The site in plain text for AI assistants (llmstxt.org): what it covers, its pages, its data files and its largest lakes. */
export function GET() {
  const lakes = getLakes();
  const standing = lakes.filter((lake) => lake.status === "exists");
  const largest = standing.filter((lake) => lake.sizeRank !== undefined && lake.acres !== undefined).slice(0, LISTED);

  const text = [
    `# ${SITE_NAME}`,
    "",
    `> Every lake in Bengaluru (Bangalore), India, in one place: ${formatCount(standing.length)} lakes that still exist and ${formatCount(lakes.length - standing.length)} that are gone. For each lake: its size, its valley, who looks after it, its water quality tests, how much of it is built over, and every map, census, satellite photo and report of it since 1799.`,
    "",
    "Every fact comes from a published source, credited on the sources page. When two sources disagree, both are kept and labelled. Kere is Kannada for lake. A filtercoffee.dev project, open source on GitHub.",
    "",
    "## Pages",
    "",
    `- [Every lake on one map](${SITE_URL}/map): search by name, Kannada name or ward; the biggest, most polluted and most built-over lakes`,
    `- [Lakes on record, 1800 to today](${SITE_URL}/timeline): every map, census, satellite photo and report of the lakes, with a copy and the original`,
    `- [Once upon a kere](${SITE_URL}/once-upon-a-kere): lakes on record as gone, when each went and what replaced it`,
    `- [Missing lakes](${SITE_URL}/missing-lakes): lakes the 2018 state survey recorded as still there that no map draws`,
    `- [Sources and credits](${SITE_URL}/sources): every source with its date, licence and credit line`,
    `- Lake pages: ${SITE_URL}/lake/{id}, one for each lake, listed in ${SITE_URL}/sitemap.xml`,
    "",
    "## Data",
    "",
    `- [lakes.json](${SITE_URL}/data/lakes.json): one row per lake with its id, names, status, location, size, valley, custodian, water class and built-over share`,
    `- [lakes.geojson](${SITE_URL}/data/lakes.geojson): the outline of every lake that has one`,
    `- ${SITE_URL}/data/lake/{id}.json: the full record behind each lake page, with the source of every fact`,
    `- [sources.json](${SITE_URL}/data/sources.json): every source key with its title, publisher, link, licence and credit`,
    "- [Source code and data pipeline](https://github.com/sagrkv/LakesOfBendakaluru)",
    "",
    `## The ${LISTED} largest lakes that still exist`,
    "",
    ...largest.map(
      (lake) =>
        `- [${lake.name}](${SITE_URL}/lake/${lake.id}): ${formatAcres(lake.acres ?? 0)} acres${lake.valley ? `, ${lake.valley} valley` : ""}${lake.ward ? `, ${lake.ward} ward` : ""}`,
    ),
    "",
  ].join("\n");

  return new Response(text, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
