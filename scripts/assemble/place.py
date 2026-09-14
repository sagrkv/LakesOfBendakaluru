"""Identity, location, size and who is responsible."""

import re
from functools import cache

from shapely.geometry import Point, shape

from common import clean
from historic_lakes import place_names, place_near

from .context import Section
from .values import acres_from_m2, num, split_list

CUSTODIANS = {
    "BBMP": "Bruhat Bengaluru Mahanagara Palike",
    "GBA": "Greater Bengaluru Authority",
    "BDA": "Bangalore Development Authority",
    "MID": "Minor Irrigation Department",
    "MI": "Minor Irrigation Department",
    "KFD": "Karnataka Forest Department",
    "Forest": "Karnataka Forest Department",
    "KLCDA": "Karnataka Lake Conservation and Development Authority",
    "KTCDA": "Karnataka Tank Conservation and Development Authority",
    "KSTDA": "Karnataka State Tourism Development Authority",
    "EN": "Engineering Department",
    "HD": "Horticulture Department",
    "Horti. Dept": "Horticulture Department",
    "ZP": "Zilla Panchayat",
    "CRPF": "Central Reserve Police Force",
    "Army Area": "Indian Army",
    "BMRCL": "Bangalore Metro Rail Corporation",
}


def identity(ctx, lake_id, reg, empri, atree):
    s = Section()
    lake = ctx.lakes.get(lake_id)
    s.set("id", lake_id, None)
    osm = [ctx.osm[l["sourceId"]] for l in ctx.linked(lake_id, "osm") if l["sourceId"] in ctx.osm]
    wd = ctx.first(lake_id, "wikidata", ctx.wikidata)
    kannada = next((o["nameKn"] for o in osm if o.get("nameKn")), None)
    s.set("nameKannada", kannada, "osm-2026-09")
    if not kannada and wd:
        s.set("nameKannada", wd.get("labelKn"), wd["source"])

    names = []
    if atree:
        names += [atree.get("name"), atree.get("nameAlt")]
    if empri:
        names += [empri.get("name"), empri.get("nameOther")]
    for o in osm:
        names += [o.get("name"), *split_list(o.get("altNames"))]
    if wd:
        names += [wd.get("labelEn"), *split_list(wd.get("aliasesEn"))]
    names = [n for n in names if not is_placeholder(n)]

    listed = lake["properties"]["name"] if lake else reg["id"]
    if is_placeholder(listed):
        # Some source rows carry "Dummy" or "Unnamed lake" as the name: use a real name if any source has one.
        real = distinct_names(names)
        point = lake["properties"].get("labelPoint") if lake else None
        near = place_near(*point, *nearby_places()) if point else None
        listed = real[0] if real else f"Unnamed lake near {near}" if near else "Unnamed lake"
    s.set("name", listed, reg_source(reg))
    s.set("namesOther", distinct_names(names, exclude=s.get("name")), None)

    s.set("kind", empri.get("kind") if empri else None, "empri-2018")
    s.set("status", *status(ctx, lake_id, reg, empri))
    return s


def reg_source(reg):
    if reg["atreeFid"]:
        return "atree-lakes"
    if reg["empriCode"]:
        return "empri-2018"
    return hist_source(reg)


def hist_source(reg):
    """Map sheet key of a tank known only from an old map, e.g. soi-57g12-1927-0001 -> soi-57g12-1927."""
    return reg["histId"].rsplit("-", 1)[0] if reg.get("histId") else None


def status(ctx, lake_id, reg, empri):
    custody = ctx.first(lake_id, "bbmp_custody", ctx.custody)
    if custody and custody.get("status") == "used for other purpose":
        return "converted", custody["source"]
    if empri and empri.get("status") == "disappeared":
        return "disappeared", "empri-2018"
    if reg.get("histId"):
        return "disappeared", hist_source(reg)
    return "exists", ("empri-2018" if empri else "atree-lakes")


PLACEHOLDER = re.compile(r"^(dummy|null|none|no name|unnamed( lake| tank)?|.{0,2})$", re.IGNORECASE)


def is_placeholder(name):
    return name is None or bool(PLACEHOLDER.match(clean(name) or ""))


@cache
def nearby_places():
    return place_names()


def distinct_names(names, exclude=None):
    """Keep one spelling per name: "Hebbal kere" and "Hebbal Kere" are the same name."""
    seen = {normal(exclude)} if exclude else set()
    out = []
    for n in names:
        n = clean(n)
        if not n or normal(n) in seen:
            continue
        seen.add(normal(n))
        out.append(n)
    return out


def normal(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def location(ctx, lake_id, reg, empri, atree):
    s = Section()
    lake = ctx.lakes.get(lake_id)
    if lake:
        p = lake["properties"]
        s.set("point", p["labelPoint"], reg_source(reg) if p["hasOutline"] else (hist_source(reg) or "empri-2018"))
        s.set("hasOutline", p["hasOutline"], None)
        if p["hasOutline"]:
            b = shape(lake["geometry"]).bounds
            s.set("bbox", [round(v, 6) for v in b], None)
            s.set("outlineSource", reg["outlineSource"], outline_source_key(reg))
    if empri:
        for field in ("district", "taluk", "hobli", "village"):
            s.set(field, empri.get(field), "empri-2018")
        s.set("surveyNumbers", split_list(empri.get("surveyNumbers")), "empri-2018")
    s.set("ward", ward_at(ctx, s.get("point")), "wards-gba-2025-369")
    s.set("insideCity", s.get("ward") is not None if s.get("point") else None, "wards-gba-2025-369")

    elevation = num(empri.get("elevationM")) if empri else None
    s.set("elevationM", elevation, "empri-2018")
    dem = ctx.stats["dem"].get(lake_id)
    if dem and elevation is None:
        s.set("elevationM", num(dem.get("shoreElevationM") or dem.get("elevationMedianM")), dem["source"])
    return s


def outline_source_key(reg):
    return {"atree": "atree-lakes", "kgis-tank": "kgis-tanks", "kgis-pond": "kgis-ponds", "kgis-wetland": "kgis-wetlands", "osm": "osm-2026-09"}.get(reg["outlineSource"])


def ward_at(ctx, point):
    if not point:
        return None
    pt = Point(point)
    for f in ctx.wards:
        if "_shape" not in f:
            f["_shape"] = shape(f["geometry"])
        if f["_shape"].contains(pt):
            p = f["properties"]
            return {
                "corporation": p["corporation"],
                "number": p["wardNumber"],
                "name": p["wardName"],
                "nameKannada": p.get("wardNameKannada"),
                "assemblyConstituency": p.get("assemblyConstituency"),
            }
    return None


def size(ctx, lake_id, reg, empri, atree):
    s = Section()
    if atree:
        s.set("outlineAcres", acres_from_m2(atree["areaM2"]), "atree-lakes")
    elif reg["outlineSource"]:
        lake = ctx.lakes.get(lake_id)
        s.set("outlineAcres", acres_from_m2(geodesic_area(lake)), outline_source_key(reg))
    custody = [ctx.custody[l["sourceId"]] for l in ctx.linked(lake_id, "bbmp_custody") if l["sourceId"] in ctx.custody]
    if custody:
        s.set("recordedAcres", round(sum(num(c["areaAcres"]) or 0 for c in custody), 2), custody[0]["source"])
    hist = ctx.hist.get(reg.get("histId"))
    if hist:
        s.set("onOldMapAcres", acres_from_m2(hist["areaM2"]), hist["source"])
    if empri:
        s.set("surveyed2018Acres", num(empri.get("extentAcres")), "empri-2018")
        s.set("maxDepthM", num(empri.get("maxDepthM")), "empri-2018")
    return s


def geodesic_area(lake):
    from pyproj import Geod

    return abs(Geod(ellps="WGS84").geometry_area_perimeter(shape(lake["geometry"]))[0])


def responsibility(ctx, lake_id, reg, empri, atree):
    s = Section()
    # Newest list wins: KTCDA 2024, then BBMP's custody list, then the 2018 inventory, then ATREE.
    ktcda = ctx.first(lake_id, "ktcda", ctx.ktcda)
    custody = ctx.first(lake_id, "bbmp_custody", ctx.custody)
    for code, source in (
        (ktcda and ktcda.get("custodian"), ktcda and ktcda["source"]),
        (custody and "BBMP", custody and custody["source"]),
        (empri and empri.get("custodian"), "empri-2018"),
        (atree and atree.get("custodianCode"), "atree-lakes"),
    ):
        if code:
            code = code.split("/")[0].strip()
            s.set("custodian", {"code": code, "name": CUSTODIANS.get(code, code)}, source)
            break
    if custody:
        s.set("developmentStatus", custody.get("status"), custody["source"])
        s.set("zone", custody.get("zone"), custody["source"])
    lms = ctx.first(lake_id, "bbmp_lms", ctx.bbmp_lms)
    if lms:
        s.set("monitoringPage", lms.get("url"), lms["source"])

    groups = []
    for link in ctx.linked(lake_id, "lake_groups"):
        g = ctx.lake_groups.get(link["sourceId"])
        if g:
            groups.append({"name": g["groupName"], "url": g.get("website") or g.get("facebook") or g.get("twitter")})
    s.set("communityGroups", groups, "citizenmatters-lake-groups-2022")
    s.set("campaignUrls", atree.get("campaignUrls") if atree else None, "atree-lakes")
    return s

