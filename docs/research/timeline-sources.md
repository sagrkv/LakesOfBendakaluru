# Timeline sources

Research done on 2026-09-14 for a per-lake timeline, from the oldest record to today.
Every link was opened by the researcher unless marked otherwise.
"Have" means the source is already in the pipeline.

## Oldest to newest

| Year | Source | What it gives per lake | Coverage | Access | Effort |
|---|---|---|---|---|---|
| 1799-1808 | Colin Mackenzie's Mysore Survey, 2 miles to an inch, British Library | Tanks, villages, irrigated land | Whole area | No public scans found | Unknown |
| 1800 | James Ross, boundaries of Purgunna of Bangalore, British Library ([Commons](https://commons.wikimedia.org/wiki/File:Survey_of_the_boundaries_of_Purgunna_of_Bangalore_(1800).png)) | Tanks not yet confirmed on the image | Most of both districts | CC BY-SA 4.0, georeferenced in Wikimaps Warper | Check the image first |
| 1843, 1854, c.1900 | Cantonment and city plans ([Commons category](https://commons.wikimedia.org/wiki/Category:Old_maps_of_Bengaluru)) | Large central tanks by name | City only | Public domain | Low |
| 1878 | Map of the Bangalore Taluk, Survey of India ([Commons](https://commons.wikimedia.org/wiki/File:Bangalore_map_1878.png)) | Tank outlines, names likely unreadable at this scan size | Old Bangalore taluk | Public domain, georeferenced | Medium |
| 1914-1917 | Survey of India one-inch sheets 57G/4, 57G/8, 57G/16, 57H/5, 57H/6, 57H/7, 57H/10 ([Zenodo](https://zenodo.org/records/8388121)) | Tank outlines and embankments, most unnamed | Nelamangala, Hoskote, Kengeri, Anekal; not the two city sheets | CC BY 4.0 | Medium, same pipeline as 1927 |
| 1915 | Revenue village maps, Karnataka Land Records ([one sample](https://commons.wikimedia.org/wiki/File:Singapura_revenue_village_map_from_1915CE.jpg)) | Every tank by survey number | One village found | Public domain | Bulk access unconfirmed |
| 1927, 1945, 1955 | Survey of India and US Army Map Service sheets | Tank drawn or not | Both districts | Have | Done |
| 1961, 1971, 1991 | Census of India district handbooks ([1961](https://censusindia.gov.in/nada/index.php/catalog/28866/download/32048/24565_1961_BAN.pdf), [1971](https://censusindia.gov.in/nada/index.php/catalog/28865/download/32047/24902_1971_BAN.pdf), [1991](https://censusindia.gov.in/nada/index.php/catalog/45466/download/49670/09_41629_1991_BAN.pdf)) | Tank-irrigated area per village, not per lake | Both districts | Free scans | OCR, match by village |
| 1960-1972 | CORONA declassified satellite photos, USGS EarthExplorer | Water, dry bed or buildings on one date, ponds under an acre | Frames over Bangalore exist (a 1965 frame used in a 2019 study) | Free if scanned, else $30 a frame | High, manual warping |
| 1971-1984 | HEXAGON declassified satellite photos, USGS | Same, at 0.6-1.2 m | Frames over Bangalore unconfirmed | $30 a scene to scan | High |
| 1972-1981 | Landsat MSS, 60 m, Earth Engine | Water or not, lakes over about 8 acres | 46 scenes, 11 under 20% cloud | Public domain | Low to medium |
| 1973-1980 | Later Survey of India one-inch editions ([Zenodo](https://zenodo.org/records/8388121)) | Surveyed outline and name | Every Bangalore District sheet: 57G/4 (1973), 57G/7 (1975), 57G/8 (1974), 57G/12 (1978), 57G/16 (1974), 57H/5 (1973), 57H/6 (1973), 57H/7 (1979), 57H/9 (1980), 57H/10 (1973); edges on Kolar sheets 57G/11 (1975, 1977) and 57H/13 (1973) | CC BY 4.0 | Medium, same pipeline as 1927 |
| 1984-2024 | EC JRC Global Surface Water v1.5 ([download](https://global-surface-water.appspot.com/download), files under `storage.googleapis.com/water-world/download2024/VER1-5/`) | Yearly water, lakes over about 2 acres | Everywhere | Free | Low; we have 1984-2021 |
| 1986 | Lakshman Rau Expert Committee report ([PDF](https://prod-qt-images.s3.amazonaws.com/indiawaterportal/import/sites/default/files/iwp2/report_of_the_expert_committee_for_preservation_restoration_or_otherwise_of_the_existing_tanks_in_bangalore_metropolitan_area_laxman_rau_1986.pdf)) | Per tank: name, hectares, condition, land use, recommendation | 127 city tanks and 262 green belt tanks | Scan, no licence stated | OCR rotated tables, match names |
| 2007 | A. T. Ramaswamy committee on land encroachment ([OpenCity](https://data.opencity.in/dataset/encorachment-of-government-lands-in-bangalore-city-urban-district-2007)) | Case stories for a few tanks | City | Public domain | Event notes only |
| 2011 | Justice N. K. Patil committee, lakes PIL ([report](https://data.opencity.in/dataset/46dffdd5-1b51-4a72-bdc0-41a0ec85c31c/resource/225ab3a3-e767-4b63-a406-7048712d6b46/download/0634635f-5928-4030-aaea-d125e488aec2.pdf)) | 386 lakes studied; per-lake annexes not found | 1,300 sq km | Main text only | Blocked on annexes |
| 2011 | Census village directory, SHRUG ([tables](https://docs.devdatalab.org/SHRUG-Metadata/Population%20Census/Tables/vd11-metadata/)) | Tank-irrigated hectares per village, tank working all year | Both districts | Clean tables | Low, village level |
| 2012-now | ISRO Bhuvan Water Bodies Information System ([portal](https://bhuvan-wbis.nrsc.gov.in/)) | Water spread over time, monthly or better | Water bodies over 2 ha, over 1 ha since 2022 | Public, no bulk download | High, one lake at a time |
| 2014-2017 | Koliwad legislature committee full report, Kannada ([OpenCity](https://data.opencity.in/dataset/bangalore-rural-urban-tanks-report)) | Per lake: survey number, encroached area, by whom, for what | Bengaluru and surrounding lakes | 273 pages, legacy Kannada font encoding | Convert text, parse tables |
| 2015-now | Dynamic World, 10 m ([Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1)) | Chance of water per image, ponds over about a quarter acre | Everywhere | CC BY 4.0 | Medium |
| 2017-2025 | Esri and Impact Observatory yearly land cover, 10 m ([catalog](https://gee-community-catalog.org/projects/S2TSLULC/)) | Water, built or bare, per year | Everywhere | CC BY 4.0 | Low |
| 2017-18 | Water Bodies Census, first | In use, encroached | Both districts | Have | Done |
| 2018 | EMPRI lake inventory | Status, extent, condition, encroachment | 1,521 water bodies | Have | Done |
| 2019-20 | CSIR-NEERI report on Bengaluru lakes ([OpenCity](https://data.opencity.in/dataset/neeri-report-on-lakes-in-bengaluru-2020)) | Encroachment, boundary, inlets, water quality | 210 city lakes | Public domain, scanned | OCR |
| 2023 | KSRSAC wetlands of Bengaluru Urban ([OpenCity](https://data.opencity.in/dataset/wetlands-of-karnataka-and-bengaluru-urban)) | 265 wetland outlines, no names | Bengaluru Urban | Public domain | Probably the same as KGIS |
| 2023-24 | Second Water Bodies Census, Ministry of Jal Shakti ([portal](https://wrcensus.mowr.gov.in/micensus/)) | In use, encroached, per water body | Karnataka reported 38,960 water bodies | Fieldwork done August 2026; only state totals public | Watch for release |
| 2024 | KTCDA lake list | Custodian | City | Have | Done |
| 2026 | Karnataka Minor Irrigation tank list ([NWDP](https://nwdp.nwic.gov.in/dataset/karnataka-minor-irrigation-tank)) | Name, village, water spread, capacity; no location or year | 146 tanks in both districts | Open CSV | Low, match by village and name |

## Known to exist, not public

The Wetlands Authority Karnataka inventory of 16,700 water bodies sits behind a login.
The 2024-2026 BBMP and Greater Bengaluru Authority encroachment surveys of 210 lakes are known only from affidavits and news.
The 2002 Lake Development Authority list, the 1990 Bangalore District Gazetteer, and the National Wetland Atlas per-lake tables were not found online.

## Suggested order

1. Extend satellite water to 2024 with JRC v1.5: low effort, every lake.
2. Trace the 1973-1980 Survey of India sheets, which cover both districts, then the 1914-1917 sheets, which cover 7 of the 10, with the existing historic map pipeline.
3. OCR the 1986 Lakshman Rau report: 389 tanks with a dated condition.
4. Add yearly 10 m land cover from 2017 to 2025 for water or built over, to today.
5. Convert and parse the Koliwad committee report for dated per-lake encroachment.
6. Check the 1800 and 1878 maps for tank detail before tracing them.

The 1973-1980 sheets give a map-drawn snapshot of every tank in the middle of the 1955-1984 gap.
CORONA and HEXAGON photos are the only record of whether those ponds held water in those years, but each frame needs manual warping, so they come last.
