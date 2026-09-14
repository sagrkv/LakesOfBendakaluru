import type { TimelineSource } from "./types";

function handbook(year: number, href: string): TimelineSource {
  return {
    id: `census-handbook-${year}`,
    from: year,
    when: String(year),
    title: "Census of India district handbook",
    holder: "Census of India",
    kind: "census",
    tells: "How much land each village watered from tanks, not each lake.",
    coverage: "Both districts",
    licence: "No licence stated",
    links: [{ label: `The ${year} handbook on the Census of India site (PDF)`, href }],
  };
}

export const CENSUSES: TimelineSource[] = [
  handbook(1961, "https://censusindia.gov.in/nada/index.php/catalog/28866/download/32048/24565_1961_BAN.pdf"),
  handbook(1971, "https://censusindia.gov.in/nada/index.php/catalog/28865/download/32047/24902_1971_BAN.pdf"),
  handbook(1991, "https://censusindia.gov.in/nada/index.php/catalog/45466/download/49670/09_41629_1991_BAN.pdf"),
  {
    id: "census-village-directory-2011",
    from: 2011,
    when: "2011",
    title: "Census village directory, SHRUG tables",
    holder: "Development Data Lab",
    kind: "census",
    tells: "How many hectares each village watered from tanks, and whether its tank worked all year.",
    coverage: "Both districts",
    licence: "CC BY-NC-SA 4.0",
    links: [
      {
        label: "The tables on Development Data Lab",
        href: "https://docs.devdatalab.org/SHRUG-Metadata/Population%20Census/Tables/vd11-metadata/",
      },
    ],
  },
  {
    id: "water-bodies-census-1",
    from: 2017,
    to: 2018,
    when: "2017-18",
    title: "Water Bodies Census, first",
    holder: "Ministry of Jal Shakti, via OpenCity",
    kind: "census",
    tells: "Whether each water body was in use or encroached.",
    coverage: "Both districts",
    licence: "Public domain",
    links: [{ label: "Open on OpenCity", key: "wbc-2017-18" }],
  },
  {
    id: "water-bodies-census-2",
    from: 2023,
    to: 2024,
    when: "2023-24",
    title: "Water Bodies Census, second",
    holder: "Ministry of Jal Shakti",
    kind: "census",
    tells: "Whether each water body is in use or encroached.",
    coverage: "Karnataka reported 38,960 water bodies",
    licence: "Not stated",
    links: [{ label: "The census portal", href: "https://wrcensus.mowr.gov.in/micensus/" }],
  },
];
