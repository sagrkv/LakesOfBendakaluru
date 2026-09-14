#!/usr/bin/env python3
"""
Wikidata items for lakes and other standing water in the ATREE extent, plus Wikipedia lead summaries.

Items are found by coordinates inside the bbox and a class that is (a subclass of) lake, reservoir,
pond, wetland, lagoon or water tank. Items with no class at all are kept when their label reads like
a lake ("Dharmambudhi Lake", "... ಕೆರೆ"). Nothing is matched to our lakes here.

Downloads: data/raw/wikidata/ (SPARQL results, entity JSON, Wikipedia summaries; reused on rerun,
delete the folder to pull fresh data).
Output:
  data/sources/wikidata.csv              one row per item
  data/sources/wikipedia_summaries.csv   one row per linked English or Kannada Wikipedia article
"""

import difflib
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import RAW, SOURCES, clean, distance_m, name_key, write_csv, write_sources  # noqa: E402

DIR = RAW / "wikidata"
USER_AGENT = "LakesOfBendakaluru/1.0 (https://filtercoffee.dev; open data project)"
SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = USER_AGENT

# south-west and north-east corners, lon lat
BOX = """
  SERVICE wikibase:box {
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point(77.18 12.65)"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point(77.96 13.48)"^^geo:wktLiteral .
  }
"""

WATER_CLASSES = {
    "Q23397": "lake",
    "Q131681": "reservoir",
    "Q3253281": "pond",
    "Q170321": "wetland",
    "Q187223": "lagoon",
    "Q6501028": "water tank",
}

BY_CLASS = f"""
SELECT DISTINCT ?item WHERE {{
  {BOX}
  ?item wdt:P31/wdt:P279* ?top .
  VALUES ?top {{ {" ".join("wd:" + q for q in WATER_CLASSES)} }}
}}
"""

# Items nobody has classified yet, whose English or Kannada label names a lake or tank.
BY_LABEL = f"""
SELECT DISTINCT ?item WHERE {{
  {BOX}
  FILTER NOT EXISTS {{ ?item wdt:P31 ?anything }}
  ?item rdfs:label ?label .
  FILTER(LANG(?label) IN ("en", "kn"))
  FILTER(REGEX(?label, "\\\\b(lake|kere|kunte|katte|tank|pond|reservoir|wetland)\\\\b|ಕೆರೆ|ಕುಂಟೆ|ಕಟ್ಟೆ|ಜಲಾಶಯ", "i"))
}}
"""

# Units of P2046 (area) -> square metres.
AREA_UNITS = {
    "Q25343": 1.0,  # square metre
    "Q712226": 1e6,  # square kilometre
    "Q35852": 1e4,  # hectare
    "Q81292": 4046.8564224,  # acre
    "Q232291": 2589988.110336,  # square mile
    "Q857027": 0.09290304,  # square foot
}

DUPLICATE_RADIUS_M = 300


def cached(path, fetch):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def get(url, params=None, accept="application/json"):
    for attempt in range(6):
        try:
            response = SESSION.get(url, params=params, headers={"Accept": accept}, timeout=120)
        except requests.ConnectionError:
            time.sleep(5 * (attempt + 1))
            continue
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(int(response.headers.get("Retry-After", 10 * (attempt + 1))))
            continue
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        if data.get("error", {}).get("code") == "maxlag":
            time.sleep(int(response.headers.get("Retry-After", 5)))
            continue
        return data
    raise RuntimeError(f"gave up on {url}")


def sparql(name, query):
    data = cached(DIR / f"sparql_{name}.json", lambda: get(SPARQL, {"query": query}, "application/sparql-results+json"))
    return [b["item"]["value"].rsplit("/", 1)[1] for b in data["results"]["bindings"]]


def entities(name, ids, props):
    """wbgetentities in batches of 50, cached as one file."""

    def fetch():
        found = {}
        for i in range(0, len(ids), 50):
            batch = get(
                API,
                {
                    "action": "wbgetentities",
                    "ids": "|".join(ids[i : i + 50]),
                    "props": props,
                    "languages": "en|kn",
                    "format": "json",
                    "maxlag": 5,
                },
            )
            found.update(batch["entities"])
            time.sleep(0.5)
        return found

    return cached(DIR / f"{name}.json", fetch)


def text(entity, field, lang):
    value = entity.get(field, {}).get(lang)
    return clean(value["value"]) if value else None


def aliases(entity, lang):
    return [clean(a["value"]) for a in entity.get("aliases", {}).get(lang, []) if clean(a["value"])]


def statements(entity, prop):
    """Best-ranked statements: preferred if any, else normal. Deprecated ones are ignored."""
    claims = [c for c in entity.get("claims", {}).get(prop, []) if c.get("rank") != "deprecated"]
    preferred = [c for c in claims if c.get("rank") == "preferred"]
    return [c["mainsnak"]["datavalue"]["value"] for c in (preferred or claims) if "datavalue" in c["mainsnak"]]


def first(entity, prop):
    values = statements(entity, prop)
    return values[0] if values else None


def item_ids(entity, prop):
    return [v["id"] for v in statements(entity, prop) if isinstance(v, dict) and "id" in v]


def area_m2(entity):
    for value in statements(entity, "P2046"):
        factor = AREA_UNITS.get(value.get("unit", "").rsplit("/", 1)[-1])
        if factor:
            return round(float(value["amount"]) * factor)
    return None


def wikidate(value):
    """A Wikidata time at its stated precision: year, month or day."""
    if not value:
        return None
    stamp = value["time"].lstrip("+")
    precision = value.get("precision", 11)
    if precision <= 9:
        return stamp[:4]
    if precision == 10:
        return stamp[:7]
    return stamp[:10]


def sitelink(entity, site):
    link = entity.get("sitelinks", {}).get(site)
    return link["title"] if link else None


def commons_category(entity):
    category = first(entity, "P373")
    if category:
        return category
    link = sitelink(entity, "commonswiki")
    return link.split(":", 1)[1] if link and link.startswith("Category:") else None


def similar(a, b):
    ka, kb = name_key(a), name_key(b)
    if not ka or not kb:
        return False
    return ka == kb or ka in kb or kb in ka or difflib.SequenceMatcher(None, ka, kb).ratio() >= 0.8


def flag_duplicates(rows):
    """Items within 300 m of each other whose names look alike are probably the same lake."""
    for row in rows:
        row["possibleDuplicateOf"] = []
    for i, a in enumerate(rows):
        names_a = [a["labelEn"], *a["aliasesEn"]]
        for b in rows[i + 1 :]:
            if a["lat"] is None or b["lat"] is None:
                continue
            if distance_m(a["lon"], a["lat"], b["lon"], b["lat"]) > DUPLICATE_RADIUS_M:
                continue
            names_b = [b["labelEn"], *b["aliasesEn"]]
            if any(similar(x, y) for x in names_a if x for y in names_b if y):
                a["possibleDuplicateOf"].append(b["qid"])
                b["possibleDuplicateOf"].append(a["qid"])


def build_rows(items, labels, source):
    rows = []
    for qid, entity in items.items():
        if "missing" in entity or entity.get("type") != "item":
            continue
        coord = first(entity, "P625")
        classes = item_ids(entity, "P31")
        heritage = item_ids(entity, "P1435")
        rows.append(
            {
                "qid": qid,
                "labelEn": text(entity, "labels", "en"),
                "labelKn": text(entity, "labels", "kn"),
                "aliasesEn": aliases(entity, "en"),
                "aliasesKn": aliases(entity, "kn"),
                "description": text(entity, "descriptions", "en"),
                "lat": round(coord["latitude"], 6) if coord else None,
                "lon": round(coord["longitude"], 6) if coord else None,
                "instanceOf": [labels.get(c, c) for c in classes],
                "instanceOfQids": classes,
                "enwiki": sitelink(entity, "enwiki"),
                "knwiki": sitelink(entity, "knwiki"),
                "image": first(entity, "P18"),
                "commonsCategory": commons_category(entity),
                "osmRelation": first(entity, "P402"),
                "osmWay": first(entity, "P10689"),
                "areaM2": area_m2(entity),
                "inception": wikidate(first(entity, "P571")),
                "geonamesId": first(entity, "P1566"),
                "heritageStatus": [labels.get(h, h) for h in heritage],
                "source": source,
            }
        )
    rows.sort(key=lambda r: int(r["qid"][1:]))
    flag_duplicates(rows)
    return rows


def summary(lang, title):
    path = DIR / "summaries" / lang / f"{quote(title, safe='')}.json"

    def fetch():
        time.sleep(0.2)
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'), safe='')}"
        return get(url, {"redirect": "true"}) or {}

    return cached(path, fetch)


def build_summaries(rows):
    out = []
    for row in rows:
        for lang in ("en", "kn"):
            title = row[f"{lang}wiki"]
            if not title:
                continue
            data = summary(lang, title)
            extract = clean(data.get("extract"))
            if not extract:
                continue
            out.append(
                {
                    "qid": row["qid"],
                    "lang": lang,
                    "title": data.get("title") or title,
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
                    "summary": extract,
                    "license": "CC BY-SA 4.0",
                    "source": f"wikipedia-{lang}",
                }
            )
    return out


COLUMNS = [
    "qid", "labelEn", "labelKn", "aliasesEn", "aliasesKn", "description", "lat", "lon",
    "instanceOf", "instanceOfQids", "enwiki", "knwiki", "image", "commonsCategory",
    "osmRelation", "osmWay", "areaM2", "inception", "geonamesId", "heritageStatus",
    "possibleDuplicateOf", "source",
]  # fmt: skip

SUMMARY_COLUMNS = ["qid", "lang", "title", "url", "summary", "license", "source"]


def main():
    qids = sorted(set(sparql("by_class", BY_CLASS)) | set(sparql("by_label", BY_LABEL)), key=lambda q: int(q[1:]))
    items = entities("entities", qids, "labels|aliases|descriptions|claims|sitelinks")
    referenced = sorted(
        {q for e in items.values() for p in ("P31", "P1435") for q in item_ids(e, p)}, key=lambda q: int(q[1:])
    )
    labels = {q: text(e, "labels", "en") or q for q, e in entities("labels", referenced, "labels").items()}

    retrieved = time.strftime("%Y-%m-%d", time.localtime((DIR / "entities.json").stat().st_mtime))
    source = f"wikidata-{retrieved[:7]}"
    rows = build_rows(items, labels, source)
    write_csv(SOURCES / "wikidata.csv", rows, COLUMNS)
    summaries = build_summaries(rows)
    write_csv(SOURCES / "wikipedia_summaries.csv", summaries, SUMMARY_COLUMNS)

    write_sources(
        "wikidata",
        [
            {
                "key": source,
                "title": "Wikidata items for lakes, reservoirs, ponds and wetlands around Bengaluru",
                "publisher": "Wikidata contributors",
                "url": "https://www.wikidata.org/",
                "license": "CC0 1.0",
                "credit": "Wikidata",
                "asOf": retrieved,
                "retrieved": retrieved,
            },
            *[
                {
                    "key": f"wikipedia-{lang}",
                    "title": f"{name} Wikipedia article lead summaries",
                    "publisher": "Wikipedia contributors",
                    "url": f"https://{lang}.wikipedia.org/",
                    "license": "CC BY-SA 4.0",
                    "credit": f"Text from {name} Wikipedia, CC BY-SA 4.0",
                    "asOf": retrieved,
                    "retrieved": retrieved,
                }
                for lang, name in (("en", "English"), ("kn", "Kannada"))
            ],
        ],
    )
    dupes = sum(1 for r in rows if r["possibleDuplicateOf"])
    print(f"wikidata: {len(rows)} items ({dupes} flagged as possible duplicates)")
    print(f"wikipedia_summaries: {len(summaries)} articles")


if __name__ == "__main__":
    main()
