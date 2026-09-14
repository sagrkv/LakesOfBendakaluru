"""Encroachment, nature, history, links and photos."""

import re

from .context import Section
from .values import flag, meaningful, num, split_list, words


def encroachment(ctx, lake_id, reg, empri, atree):
    s = Section()
    if empri:
        s.set("koliwadAcres", num(empri.get("encroachmentKoliwadAcres")), "empri-2018")
        s.set("pct2018", num(empri.get("encroachmentPct")), "empri-2018")
        s.set("by", words(empri.get("encroachedBy")), "empri-2018")
        s.set("for", meaningful(empri.get("encroachedFor")), "empri-2018")
        s.set("side", meaningful(empri.get("encroachmentDirection")), "empri-2018")
        s.set("dumping", meaningful(empri.get("dumpingType")), "empri-2018")
        s.set("otherIssues", meaningful(empri.get("otherIssues")), "empri-2018")
    maps = []
    for source in ("landrecords_survey", "landrecords_digital"):
        for link in ctx.linked(lake_id, source):
            r = ctx.landrecords.get(link["sourceId"])
            # Land records list the same map under several links; keep each map once.
            if r and r.get("mapImageUrl") and all(m["url"] != r["mapImageUrl"] for m in maps):
                maps.append({"village": r.get("village"), "surveyNumber": r.get("surveyNumber"), "url": r["mapImageUrl"], "source": r["source"]})
    s.set("officialMaps", maps, "per-entry")
    wbc = ctx.first(lake_id, "wbc2018", ctx.wbc)
    if wbc:
        s.set("census2018Encroached", flag(wbc.get("encroached")), wbc["source"])
    return s


def nature(ctx, lake_id, reg, empri, atree):
    s = Section()
    gbif = ctx.stats["gbif"].get(lake_id)
    if gbif:
        s.set(
            "birds",
            {k: v for k, v in {"species": num(gbif.get("birdSpecies")), "records": num(gbif.get("birdRecords")), "top": split_list(gbif.get("topBirds"))}.items() if v},
            gbif["source"],
        )
        s.set(
            "allSpecies",
            {k: v for k, v in {"species": num(gbif.get("species")), "records": num(gbif.get("records")), "firstYear": num(gbif.get("firstYear")), "lastYear": num(gbif.get("lastYear"))}.items() if v},
            gbif["source"],
        )
    species = ctx.gbif_species.get(lake_id, [])
    if species:
        s.set(
            "threatened",
            [{"name": r.get("vernacularName") or r["scientificName"], "scientificName": r["scientificName"], "iucn": r["iucnCategory"]} for r in species if r.get("iucnCategory") in ("VU", "EN", "CR", "NT")],
            species[0]["source"],
        )
    inat = ctx.stats["inaturalist"].get(lake_id)
    if inat:
        s.set(
            "observations",
            {k: v for k, v in {"count": num(inat.get("observations")), "species": num(inat.get("species")), "researchGrade": num(inat.get("researchGrade")), "top": split_list(inat.get("topTaxa")), "lastObserved": inat.get("lastObserved")}.items() if v},
            inat["source"],
        )
    wc = ctx.stats["worldcover"].get(lake_id)
    if wc:
        ring = {k: num(wc.get(f"ring{k[0].upper()}{k[1:]}Pct")) for k in ("built", "tree", "grass", "crop", "bare", "water", "shrub", "wetland")}
        s.set("landAround", {k: v for k, v in ring.items() if v}, wc["source"])
        s.set("builtInsideOutlinePct", num(wc.get("insideBuiltPct")), wc["source"])
    if empri:
        s.set("fauna2018", words(empri.get("fauna")), "empri-2018")
        s.set("plants2018", words(empri.get("aquaticFlora")), "empri-2018")
        s.set("weeds2018", meaningful(empri.get("weeds")), "empri-2018")
    return s


def history(ctx, lake_id, reg, empri, atree):
    s = Section()
    if empri:
        s.set("yearBuilt", num(empri.get("year")), "empri-2018")
        s.set("rejuvenated", flag(empri.get("rejuvenated")), "empri-2018")
        s.set("yearRejuvenated", num(empri.get("atlasYearRejuvenated")), "empri-2018")
        if empri.get("status") == "disappeared":
            s.set("nowOccupiedBy", empri.get("convertedTo"), "empri-2018")
            s.set("convertedBy", words(empri.get("convertedBy")), "empri-2018")
            s.set("goneBy", year_of(empri.get("visitDate")), "empri-2018")
        s.set("surroundings2018", empri.get("surroundingArea"), "empri-2018")
        s.set("remarks2018", empri.get("remarks"), "empri-2018")

    traced = ctx.hist.get(reg.get("histId"))
    if traced:
        # Known only from an old map: no list, survey or record mentions this tank.
        s.set("knownOnlyFromOldMap", True, traced["source"])
        s.set("oldMapConfidence", traced["confidence"], traced["source"])
        # onMap<edition>: the 1914-1917 sheets are edition 1914, the 1973-1980 sheets 1975; the sheet's own year is its source's date.
        # Single-year sheets (1927, 1945, 1955) are their own edition.
        s.set(f"onMap{traced.get('edition', traced['year'])}", True, traced["source"])

    hist = ctx.stats["historic_presence"].get(lake_id)
    if hist:
        for col, value in hist.items():
            m = re.fullmatch(r"onMap(\d{4})", col)
            if m and value not in (None, ""):
                s.set(col, flag(value), hist.get(f"source{m.group(1)}") or hist["source"])

    jrc = ctx.stats["jrc_water"].get(lake_id)
    if jrc:
        s.set("lastSeenWithWater", num(jrc.get("lastYearWithWater")), jrc["source"])

    # The 1986 Lakshman Rau Expert Committee lists: the tank as the committee saw it and what it proposed.
    rau = ctx.first(lake_id, "rau1986", ctx.rau1986)
    if rau:
        entry = {
            "list": rau["list"], "status": rau.get("status"), "nameAsPrinted": rau.get("name"), "tankNo": rau.get("tankNo"),
            "areaHa": num(rau.get("areaHa")), "condition": rau.get("condition"), "landUse": rau.get("landUse"),
            "recommendation": rau.get("recommendation"), "agency": rau.get("agency"), "zone": rau.get("zone"), "taluk": rau.get("taluk"),
        }
        s.set("rau1986", {k: v for k, v in entry.items() if v not in (None, "")}, rau["source"])
    return s


def year_of(date):
    return int(date[:4]) if date and re.match(r"\d{4}", date) else None


def links(ctx, lake_id, reg, empri, atree):
    s = Section()
    wd = ctx.first(lake_id, "wikidata", ctx.wikidata)
    osm = [ctx.osm[l["sourceId"]] for l in ctx.linked(lake_id, "osm") if l["sourceId"] in ctx.osm]
    if wd:
        s.set("wikidata", wd["qid"], wd["source"])
        s.set("commonsCategory", wd.get("commonsCategory"), wd["source"])
        wiki = {}
        for lang in ("en", "kn"):
            title = wd.get(f"{lang}wiki")
            if title:
                summary = ctx.wiki_summaries.get(wd["qid"], {}).get(lang)
                wiki[lang] = {"title": title, "url": f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"}
                if summary:
                    wiki[lang]["summary"] = summary["summary"]
        s.set("wikipedia", wiki, "wikipedia-en")
    s.set("osm", [f"https://www.openstreetmap.org/{o['osmId']}" for o in osm], "osm-2026-09")
    lms = ctx.first(lake_id, "bbmp_lms", ctx.bbmp_lms)
    if lms:
        s.set("bbmpLakePage", lms.get("url"), lms["source"])
    ids = {
        "atreeFid": reg.get("atreeFid"),
        "empriCode": reg.get("empriCode"),
        "ldaId": atree.get("ldaId") if atree else None,
        "kgisTankId": first_id(ctx, lake_id, "kgis_tanks"),
        "miTankId": first_id(ctx, lake_id, "mi_tanks"),
        "waterBodyCensusId": first_id(ctx, lake_id, "wbc2018"),
        "bbmpLmsId": first_id(ctx, lake_id, "bbmp_lms"),
    }
    s.set("ids", {k: v for k, v in ids.items() if v}, None)
    return s


def first_id(ctx, lake_id, source):
    links = ctx.linked(lake_id, source)
    return links[0]["sourceId"] if links else None


def photos(ctx, lake_id):
    out = []
    for r in sorted(ctx.photos.get(lake_id, []), key=lambda r: int(r["rank"])):
        out.append(
            {
                k: v
                for k, v in {
                    "title": r["title"].removeprefix("File:"),
                    "page": r["pageUrl"],
                    "thumb": r["thumbUrl"],
                    "width": num(r.get("width")),
                    "height": num(r.get("height")),
                    "author": r.get("author"),
                    "license": r.get("license"),
                    "credit": r.get("credit"),
                    "date": r.get("dateTaken"),
                }.items()
                if v
            }
        )
    return out
