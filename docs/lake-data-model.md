# Lake data model

This is the structure of everything we know about each lake.
It says what a lake record holds, where each fact comes from, how sources are matched to lakes, and how to rebuild it.

## Rules

Every lake has one permanent ID that we own.
Once assigned it never changes, even if the lake is renamed or a source is rebuilt.

Every fact carries only a short source key, such as `kspcb-2025-11`.
The key resolves through `public/data/sources.json`, which holds the title, publisher, link, license, credit line and dates once per source.
Lake pages show the plain fact with a "See source" link, never a trail of source records.

When two sources disagree, we keep both and label them, instead of picking one silently.
Area is the common case: the drawn outline, the land record and the 2018 survey all give different numbers.

Sources are matched to lakes by location first, then by name.
Matching by name alone is wrong for Bengaluru: dozens of names repeat, and the old name-only OpenStreetMap matches pointed at lakes up to 70 km away.
A name is only used to choose between lakes that are already close, or, when a source has no location at all, when exactly one lake has that name.

Facts that change over time (water quality, water presence) are kept as dated entries, not overwritten.

## Which lakes are in the list

Every lake that exists or is known to have existed.
That is the 1,350 outlines from the ATREE copy of the BBMP master list, plus every water body in the 2018 EMPRI inventory that is not one of them.
The inventory lists 1,521 water bodies, 838 of which have disappeared.

A disappeared lake has no current outline, only a location, survey numbers, a recorded extent and what occupies the site now.
It is drawn as a point.
These lakes make up the "Once upon a kere" page.

An inventory lake that still exists but is not in the ATREE map borrows the nearest shape from the KGIS tank, pond or wetland map, or OpenStreetMap, within 50 m of its point.
Survey points are often a few metres off the pond they mark.
A shape under 5% of the lake's recorded 2018 extent is not borrowed: it is a different, smaller pond.
An existing lake that still has no shape is not drawn on the map; it is listed on the "Missing lakes of Bangalore" page.

## Files

```
data/raw/<source>/                 small downloads exactly as fetched (committed)
data/cache/<source>/               large downloads: PDFs, rasters, API responses (ignored, re-fetched)
data/sources/<source>.csv|geojson  one clean table per source, one row per source record
data/sources/<source>.sources.json citation for each source key
data/registry.csv                  lake ID, what anchors it (ATREE outline or inventory row), how they were paired
data/lakes.geojson                 every lake as an outline or a point, the input for per-lake stats
data/crosswalk.csv                 every link from a source record to a lake, with method, distance and name score
data/crosswalk_overrides.csv       hand corrections: add or remove a link (optional; always wins)
public/data/                       what the site reads
```

Site outputs:

| File | Holds |
|---|---|
| `lakes.json` | one summary row per lake: name, status, point, acres, size rank, valley, custodian, ward, latest water class, built and encroached share, campaign, first photo, year built, position `xy` in the `hero.json` frame |
| `lakes.geojson` | outlines of every lake that has one |
| `districts.geojson` | the outer edge of Bengaluru Urban and Bengaluru North (formerly Bengaluru Rural) districts, from OpenStreetMap |
| `city.geojson` | the Greater Bengaluru city limit: the 369 wards of the 2025 ward map merged |
| `past.json` | one lean row per lake that disappeared or was converted, for the "Once upon a kere" page: id, name, acres, valley, `xy`, `goneBy`, `lastSeenWithWater`, `onMap` years, `knownOnlyFromOldMap`, `convertedBy`, `nowOccupiedBy` |
| `past-sheet.svg` | the city as a sheet of ink paper with a hole where each past lake was, six times its real width, and a faint dot for each lake still there |
| `missing.json` | one lean row per lake recorded as existing that no map draws (status exists, no outline, a point), for the "Missing lakes of Bangalore" page, largest first by 2018 extent: id, name, Kannada name, kind, 2018 acres, village, taluk, ward, custodian name, 2018 condition and uses, `onList2024` (custodian from the 2024 KTCDA list), `monitoringPage`, `waterSeen` (last year satellites saw water), `onMap` years, `xy` |
| `missing-sheet.svg` | the city as dots in the `hero.json` frame: a faint dot for each lake a map draws, an ink ring for each missing lake |
| `lake/<id>.json` | the full record for one lake page, including its monthly water quality series |
| `sources.json` | every source key used, with title, publisher, link, license, credit and dates |
| `hero.json` | simplified outlines of existing lakes for the home page drawing, in a frame that covers every lake point and outline |
| `openers.json` | ids of lakes the opening screen may show: existing, with a sheet whose room is at least 40 m wide and 15% of the lake's long side |

## Rebuilding

```
.venv/bin/python scripts/sources/<source>.py   fetch and clean one source
.venv/bin/python scripts/build.py              registry -> crosswalk -> public/data
.venv/bin/python scripts/run_stats.py          per-lake stats on the full list (then build.py again)
```

Set up the environment once with `uv venv .venv --python 3.13 && uv pip install -p .venv -r scripts/requirements.txt`.

## The lake record

Each section is an object of plain facts plus a `src` map from fact name to source key.
A `src` value of `per-entry` means each item in that list carries its own `source`.
Facts we do not know are left out rather than set to null.

### Identity (top level)

| Field | Source |
|---|---|
| `id` - permanent slug, also the URL | ours |
| `name` - the English Wikipedia title if the lake has an article, else the ATREE name, else the inventory name. A placeholder such as "Dummy" or "Unnamed lake" is replaced by the first real name any source gives, else "Unnamed lake near" the ward or nearest village | Wikipedia, ATREE, 2018 inventory, 2025 ward map, OSM places |
| `nameKannada` | OpenStreetMap, Wikidata |
| `namesOther` - every other name the lake goes by | ATREE, 2018 inventory, OSM, Wikidata |
| `kind` - kere (large), katte (medium), kunte (small pond) | 2018 inventory |
| `status` - exists, disappeared, converted | 2018 inventory, BBMP custody list |

### `location`

| Field | Source |
|---|---|
| `point`, `bbox`, `hasOutline`, `outlineSource` | ATREE, KGIS, OSM or the inventory point |
| `district`, `taluk`, `hobli`, `village`, `surveyNumbers` | 2018 inventory |
| `ward` - corporation, number, name, Kannada name, assembly constituency | 2025 Greater Bengaluru ward map, by location |
| `insideCity` | 2025 ward map |
| `elevationM` | 2018 inventory, else Copernicus DEM |

### `size`

| Field | Source |
|---|---|
| `outlineAcres` - measured from the outline | ATREE, KGIS or OSM |
| `recordedAcres` - extent on land records | BBMP custody list |
| `surveyed2018Acres` | 2018 inventory |
| `maxDepthM` | 2018 inventory |

### `responsibility`

| Field | Source |
|---|---|
| `custodian` - code and agency name; newest list wins | KTCDA 2024, BBMP custody list, 2018 inventory, ATREE |
| `developmentStatus`, `zone` | BBMP custody list |
| `monitoringPage` | BBMP Lake Monitoring System |
| `communityGroups`, `campaignUrls` | Citizen Matters directory, ATREE |

Ward councillor names and phone numbers are not published: the only source is the ward council whose term ended in 2020.

### `water`

| Field | Source |
|---|---|
| `valley` - the river basin the lake drains to, computed the same way for every lake | Copernicus DEM flow routing |
| `downstream`, `upstream`, `catchmentKm2` | ATREE streams inside BBMP, DEM flow routing elsewhere, the 2018 atlas as fallback |
| `inletDrains`, `wasteWeirs`, `sluiceGates`, `culverts`, `checkDams`, `islands` | 2018 inventory |
| `conditionIn2018`, `sewageInflowFrom`, `pollutant`, `uses`, `sourceOfWater` | 2018 inventory |
| `presence` - share of satellite passes with water 1984-2024, permanent, seasonal, lost, gained, first and last year with water | JRC Global Surface Water |
| `yearly` - water acres per year 1984-2021 | JRC Global Surface Water |
| `current` - open water, floating weed and dry share from recent Sentinel-2 images | Sentinel-2 |
| `nearestTreatmentPlant` - name, capacity, distance within 3 km | BWSSB |

Floating weed reads as land to JRC, so weed-choked lakes such as Bellandur show low water presence.
`current.weedCoverPct` is the check on that.

### `waterQuality`

| Field | Source |
|---|---|
| `stations` - KSPCB monitoring stations on the lake | KSPCB |
| `latest` - the most recent month, one entry per station | KSPCB |
| `series` - every month since July 2023: month, station, class (A-E), values, below-detection list, source | KSPCB |
| `units` - unit per measure | KSPCB |
| `olderTests` - 2011 Mines and Geology, 2015 lake sheet and Jakkur series, 2021 national monitoring | OpenCity datasets |
| `surveyTests` - inlet and outlet tests from 2017-18 | 2018 inventory |

### `encroachment`

| Field | Source |
|---|---|
| `koliwadAcres` - encroached extent reported by the 2017 legislature committee | 2018 inventory |
| `pct2018`, `by`, `for`, `side`, `dumping`, `otherIssues` | 2018 inventory |
| `officialMaps` - land records map images by village and survey number | Karnataka land records |
| `census2018Encroached` | Water Bodies Census (its status fields are unreliable) |

We store areas and counts, never encroachers' names.

### `nature`

| Field | Source |
|---|---|
| `birds` - species, records, top species | GBIF (mostly eBird) |
| `allSpecies`, `threatened` | GBIF |
| `observations` | iNaturalist |
| `landAround` - built, tree, grass, crop, bare, water share within 500 m; `builtInsideOutlinePct` | ESA WorldCover 2021 |
| `fauna2018`, `plants2018`, `weeds2018` | 2018 inventory |

### `history`

| Field | Source |
|---|---|
| `yearBuilt`, `rejuvenated`, `yearRejuvenated` | 2018 inventory |
| `onMap<year>` - drawn on that year's survey map | Survey of India and US Army Map Service sheets |
| `lastSeenWithWater` | JRC Global Surface Water |
| `nowOccupiedBy`, `convertedBy`, `goneBy` - for disappeared lakes | 2018 inventory |
| `surroundings2018`, `remarks2018` | 2018 inventory |

### `sheet`

The lake cut out at its outline, for the opening screen and the lake page.
Only lakes with an outline have one.
Everything is in metres of UTM 43N, with (0, 0) at the outline's top-left corner, x growing east and y growing down.

| Field | Holds |
|---|---|
| `w`, `h` | width and height of the outline's bounding box |
| `origin` | UTM 43N easting and northing of the top-left corner, so a map image in the same projection lines up with the sheet |
| `d` | SVG path of every ring, outer rings and islands as separate subpaths; draw with fill-rule evenodd |
| `room` - `x`, `y`, `w`, `h` | the widest rectangle inside the water whose height is at least 0.3 of its width, where the name is set |
| `span` - `x1`, `y1`, `x2`, `y2`, `m` | the two outline points farthest apart and the distance between them |

The path is simplified to within the larger of 1 m and the long side divided by 900.
The room fits inside both the real outline and the simplified path.

### `links`, `photos`, `events`

| Field | Source |
|---|---|
| `wikipedia` (English and Kannada, with lead summary), `wikidata`, `commonsCategory`, `osm`, `bbmpLakePage` | Wikidata, Wikipedia, OSM, BBMP |
| `ids` - ATREE, inventory, LDA, KGIS, Minor Irrigation, Water Bodies Census, BBMP IDs | each source |
| `photos` - thumbnail, page, author, license, credit | Wikimedia Commons |
| `events` - dated incidents and actions | none yet; to be built from news and official orders |

## Credit

The outlines are ATREE-CSEI data under CC BY, and the site must credit them.
JRC, Sentinel, WorldCover, Copernicus DEM, GBIF and Wikidata need their credit lines too; each is in `sources.json`.
OpenStreetMap data is ODbL, which requires credit and keeps the data open.
Government reports on OpenCity are marked public domain.
