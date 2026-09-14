/**
 * Types for the files in public/data, written by scripts/build.py.
 * See docs/lake-data-model.md. Facts that are not known are left out, never null.
 * No file access here: the map and the opening screen use these in the browser.
 */

export type Status = "exists" | "disappeared" | "converted";
export type Kind = "kere" | "katte" | "kunte";
export type WaterClass = "A" | "B" | "C" | "D" | "E";
export type LngLat = [number, number];
export type BBox = [number, number, number, number];

/** A map from fact name to source key (or keys). "per-entry" means each list item has its own `source`. */
export type Src = Record<string, string | string[]>;

/** One row of lakes.json: what a list, a map or a collection needs without opening the lake file. */
export type LakeSummary = {
  id: string;
  name: string;
  nameKannada?: string;
  status: Status;
  kind?: Kind;
  point?: LngLat;
  bbox?: BBox;
  hasOutline: boolean;
  acres?: number;
  valley?: string;
  custodian?: string;
  corporation?: string;
  ward?: string;
  waterClass?: WaterClass;
  waterClassMonth?: string;
  nowOccupiedBy?: string;
  builtPct?: number;
  encroachedPct?: number;
  campaign?: true;
  photo?: string;
  yearBuilt?: number;
  /** 1 is the largest existing lake. */
  sizeRank?: number;
  /** Position in the hero.json frame. */
  xy?: [number, number];
};

/** A lake up or down the chain. No id when it is a river or a name with no lake page. */
export type LakeRef = { id?: string; name: string };

/** The cut-out: the outline in metres, y down, origin at the outline's top-left. */
export type Sheet = {
  w: number;
  h: number;
  d: string;
  /** The largest rectangle inside the water, where the name is set. */
  room: { x: number; y: number; w: number; h: number };
  /** The longest straight line across the lake. */
  span: { x1: number; y1: number; x2: number; y2: number; m: number };
  /** Easting and northing of the top-left corner in EPSG:32643 (UTM 43N). */
  origin: [number, number];
};

export type Ward = {
  corporation?: string;
  number?: number;
  name?: string;
  nameKannada?: string;
  assemblyConstituency?: string;
};

export type WaterReading = {
  month: string;
  station: string;
  class?: WaterClass;
  values: Record<string, number>;
  belowDetection?: string[];
  source: string;
};

export type Photo = {
  title: string;
  page: string;
  thumb: string;
  width: number;
  height: number;
  author?: string;
  license?: string;
  credit: string;
  date?: string;
};

export type LakeRecord = {
  id: string;
  name: string;
  src: Src;
  nameKannada?: string;
  namesOther?: string[];
  kind?: Kind;
  status: Status;
  sheet?: Sheet;
  location?: {
    src: Src;
    point?: LngLat;
    bbox?: BBox;
    hasOutline?: boolean;
    outlineSource?: string;
    district?: string;
    taluk?: string;
    hobli?: string;
    village?: string;
    surveyNumbers?: string[];
    ward?: Ward;
    insideCity?: boolean;
    elevationM?: number;
  };
  size?: {
    src: Src;
    outlineAcres?: number;
    recordedAcres?: number;
    surveyed2018Acres?: number;
    onOldMapAcres?: number;
    maxDepthM?: number;
  };
  responsibility?: {
    src: Src;
    custodian?: { code: string; name: string };
    developmentStatus?: string;
    zone?: string;
    monitoringPage?: string;
    communityGroups?: { name: string; url?: string }[];
    campaignUrls?: string[];
  };
  water?: {
    src: Src;
    valley?: string;
    downstream?: LakeRef;
    upstream?: LakeRef[];
    catchmentKm2?: number;
    inletDrains?: number;
    wasteWeirs?: number;
    sluiceGates?: number;
    culverts?: number;
    checkDams?: number;
    islands?: number;
    conditionIn2018?: string[];
    sewageInflowFrom?: string[];
    pollutant?: string;
    uses?: string[];
    sourceOfWater?: string;
    presence?: {
      occurrencePct: number;
      permanentPct: number;
      seasonalPct: number;
      neverWaterPct: number;
      lostPct: number;
      gainedPct: number;
      firstYear?: number;
      lastYear?: number;
      lowConfidence: boolean;
    };
    yearly?: { year: number; waterAcres: number; observedAcres: number }[];
    current?: {
      season: string;
      from: string;
      to: string;
      openWaterPct: number;
      weedCoverPct: number;
      dryOrBuiltPct: number;
      lowConfidence: boolean;
      source: string;
    }[];
    nearestTreatmentPlant?: { name: string; capacityMld?: number; distanceM: number };
  };
  waterQuality?: {
    src: Src;
    stations?: { id: string; name: string; point?: LngLat; firstMonth: string; lastMonth: string }[];
    latest?: WaterReading[];
    series?: WaterReading[];
    units?: Record<string, string>;
    olderTests?: {
      date: string;
      station?: string;
      point?: string;
      statistic?: string;
      values: Record<string, number>;
      source: string;
    }[];
    surveyTests?: { date: string; point?: string; values: Record<string, number> }[];
  };
  encroachment?: {
    src: Src;
    koliwadAcres?: number;
    pct2018?: number;
    by?: string[];
    for?: string;
    side?: string;
    dumping?: string;
    otherIssues?: string;
    officialMaps?: { village: string; surveyNumber: string; url: string; source: string }[];
    census2018Encroached?: boolean;
  };
  nature?: {
    src: Src;
    birds?: { species: number; records: number; top: string[] };
    allSpecies?: { species?: number; records: number; firstYear?: number; lastYear?: number };
    threatened?: { name: string; scientificName: string; iucn: string }[];
    observations?: {
      count: number;
      species?: number;
      researchGrade?: number;
      top?: string[];
      lastObserved?: string;
    };
    landAround?: Partial<Record<"built" | "tree" | "grass" | "crop" | "bare" | "shrub" | "water", number>>;
    builtInsideOutlinePct?: number;
    fauna2018?: string[];
    plants2018?: string[];
    weeds2018?: string;
  };
  history?: {
    src: Src;
    yearBuilt?: number;
    rejuvenated?: boolean;
    yearRejuvenated?: number;
    onMap1927?: boolean;
    onMap1945?: boolean;
    onMap1955?: boolean;
    knownOnlyFromOldMap?: boolean;
    oldMapConfidence?: string;
    lastSeenWithWater?: number;
    nowOccupiedBy?: string;
    convertedBy?: string[];
    goneBy?: number;
    surroundings2018?: string;
    remarks2018?: string;
  };
  links?: {
    src: Src;
    wikipedia?: Partial<Record<"en" | "kn", { title: string; url: string; summary?: string }>>;
    wikidata?: string;
    commonsCategory?: string;
    osm?: string[];
    bbmpLakePage?: string;
    ids?: Record<string, string>;
  };
  photos?: Photo[];
  events: unknown[];
};

export type Source = {
  key: string;
  title: string;
  publisher?: string;
  url?: string;
  license?: string;
  credit?: string;
  asOf?: string;
  retrieved?: string;
};

export type HeroShape = { id: string; name: string; acres: number; d: string };
export type Hero = { width: number; height: number; shapes: HeroShape[] };
