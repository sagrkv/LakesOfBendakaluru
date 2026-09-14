"""Water and drainage, and water quality."""

from collections import defaultdict

from common import distance_m

from .context import Section
from .values import ACRE_M2, flag, meaningful, num, split_list, words

PLANT_WITHIN_M = 3000


def water(ctx, lake_id, reg, empri, atree):
    s = Section()
    cascade = ctx.stats["cascade"].get(lake_id)
    if cascade:
        src = cascade["source"]
        s.set("downstream", lake_ref(ctx, cascade.get("downstreamKey")), src)
        s.set("upstream", [r for r in (lake_ref(ctx, k) for k in (cascade.get("upstreamKeys") or "").split(";")) if r], src)
        s.set("catchmentKm2", num(cascade.get("catchmentKm2")), src)
        # Computed the same way for every lake, so valleys are comparable across the list.
        s.set("valley", cascade.get("valleyBasin"), src)

    if empri:
        for field in ("inletDrains", "wasteWeirs", "sluiceGates", "culverts", "checkDams", "islands"):
            s.set(field, num(empri.get(field)), "empri-2018")
        s.set("conditionIn2018", words(empri.get("presentStatus")), "empri-2018")
        s.set("sewageInflowFrom", words(empri.get("sewageInflow")), "empri-2018")
        s.set("pollutant", meaningful(empri.get("pollutant")), "empri-2018")
        s.set("uses", words(empri.get("waterUsage")), "empri-2018")
        s.set("sourceOfWater", meaningful(empri.get("atlasSourceOfWater")), "empri-2018")
        if "downstream" not in s:
            s.set("downstream", atlas_ref(ctx, lake_id, empri.get("atlasDownstream")), "empri-2018")
        if "upstream" not in s:
            s.set("upstream", [r for r in (atlas_ref(ctx, lake_id, n) for n in split_list(empri.get("atlasUpstream"))) if r], "empri-2018")

    jrc = ctx.stats["jrc_water"].get(lake_id)
    if jrc:
        presence = {
            "occurrencePct": num(jrc.get("occurrenceMean")),
            "permanentPct": num(jrc.get("pctPermanent")),
            "seasonalPct": num(jrc.get("pctSeasonal")),
            "neverWaterPct": num(jrc.get("pctNeverWater")),
            "lostPct": sum_num(jrc, "pctLostPermanent", "pctLostSeasonal"),
            "gainedPct": sum_num(jrc, "pctNewPermanent", "pctNewSeasonal"),
            "firstYear": num(jrc.get("firstYearWithWater")),
            "lastYear": num(jrc.get("lastYearWithWater")),
            "lowConfidence": flag(jrc.get("lowConfidence")),
        }
        s.set("presence", {k: v for k, v in presence.items() if v is not None}, jrc["source"])

    yearly = []
    for r in sorted(ctx.jrc_yearly.get(lake_id, []), key=lambda r: int(r["year"])):
        observed = num(r.get("observedM2")) or 0
        if observed <= 0:
            continue
        wet = (num(r.get("waterPermanentM2")) or 0) + (num(r.get("waterSeasonalM2")) or 0)
        yearly.append({"year": int(r["year"]), "waterAcres": round(wet / ACRE_M2, 2), "observedAcres": round(observed / ACRE_M2, 2)})
    s.set("yearly", yearly, ctx.jrc_yearly[lake_id][0]["source"] if yearly else None)

    # Both seasons: a single one misleads, because several big lakes were drained in spring 2026.
    seasons = []
    for season in ("postmonsoon", "dry"):
        r = ctx.sentinel2.get(lake_id, {}).get(season)
        if not r:
            continue
        entry = {
            "season": "after monsoon" if season == "postmonsoon" else "dry season",
            "from": r.get("compositeStart"),
            "to": r.get("compositeEnd"),
            "openWaterPct": num(r.get("openWaterPct")),
            "weedCoverPct": num(r.get("floatingVegetationPct")),
            "dryOrBuiltPct": num(r.get("dryOrBuiltPct")),
            "lowConfidence": flag(r.get("lowConfidence")),
            "source": r["source"],
        }
        seasons.append({k: v for k, v in entry.items() if v is not None})
    s.set("current", seasons, "per-entry")

    point = ctx.lakes.get(lake_id, {}).get("properties", {}).get("labelPoint")
    plant = nearest_plant(ctx, point)
    if plant:
        s.set("nearestTreatmentPlant", plant[0], plant[1])
    return s


def sum_num(row, *cols):
    values = [num(row.get(c)) for c in cols]
    return None if all(v is None for v in values) else round(sum(v or 0 for v in values), 2)


def lake_ref(ctx, key):
    if not key:
        return None
    lake_id = key if key in ctx.registry else ctx.by_fid.get(key)
    if not lake_id:
        return None
    return {"id": lake_id, "name": ctx.lakes[lake_id]["properties"]["name"] if lake_id in ctx.lakes else lake_id}


def atlas_ref(ctx, lake_id, name):
    """
    The 2018 atlas names the lake upstream or downstream. Resolve the name to a lake
    within 5 km; a river or an unresolvable name is kept as a plain name.
    """
    name = meaningful(name)
    if not name:
        return None
    here = ctx.lakes.get(lake_id, {}).get("properties", {}).get("labelPoint")
    found = ctx.find_by_name(name, here, within_m=5000, exclude=lake_id) if here else None
    return {"id": found, "name": ctx.lakes[found]["properties"]["name"]} if found else {"name": name}


def nearest_plant(ctx, point):
    if not point:
        return None
    best = None
    for p in ctx.treatment_plants:
        d = distance_m(point[0], point[1], p["lon"], p["lat"])
        if d <= PLANT_WITHIN_M and (best is None or d < best[0]):
            best = (d, p)
    if not best:
        return None
    d, p = best
    return {"name": p["name"], "capacityMld": num(p["capacityMld"]), "distanceM": round(d)}, p["source"]


def quality(ctx, lake_id, reg, empri, atree):
    """Monthly readings from every KSPCB station on the lake, plus the 2018 inventory's own tests."""
    s = Section()
    stations = [ctx.kspcb_stations[l["sourceId"]] for l in ctx.linked(lake_id, "kspcb") if l["sourceId"] in ctx.kspcb_stations]
    series = []
    units = {}
    for st in stations:
        by_month = defaultdict(list)
        for r in ctx.kspcb_readings.get(st["stationId"], []):
            by_month[r["month"]].append(r)
        for month, readings in by_month.items():
            values, below = {}, []
            for r in readings:
                units[r["parameter"]] = r.get("unit")
                v = num(r.get("value"))
                if v is not None:
                    values[r["parameter"]] = v
                if flag(r.get("belowDetection")):
                    below.append(r["parameter"])
            entry = {"month": month, "station": st["stationId"], "class": readings[0].get("useClass"), "values": values, "source": readings[0]["source"]}
            if below:
                entry["belowDetection"] = sorted(below)
            series.append(entry)
    series.sort(key=lambda e: (e["month"], e["station"]))

    if stations:
        s.set(
            "stations",
            [
                {k: v for k, v in {"id": st["stationId"], "name": st["stationName"], "point": point_of(st), "firstMonth": st.get("firstMonth"), "lastMonth": st.get("lastMonth")}.items() if v}
                for st in stations
            ],
            stations[0]["source"],
        )
    if series:
        last_month = series[-1]["month"]
        latest = [e for e in series if e["month"] == last_month]
        s.set("latest", latest, latest[0]["source"])
        s.set("series", series, "per-entry")
        s.set("units", {k: v for k, v in units.items() if v}, None)

    older = defaultdict(dict)
    for link in ctx.linked(lake_id, "wq_historic"):
        for r in ctx.wq_historic.get(link["sourceId"], []):
            v = num(r.get("value"))
            if v is None:
                continue
            key = (r["source"], r["stationName"], r.get("sampleLocation"), r.get("date"), r.get("statistic"))
            older[key][r["parameter"]] = v
    s.set(
        "olderTests",
        [
            {k: v for k, v in {"date": d, "station": st, "point": loc, "statistic": stat, "values": vals, "source": src}.items() if v}
            for (src, st, loc, d, stat), vals in sorted(older.items(), key=lambda kv: str(kv[0][3]))
        ],
        "per-entry",
    )

    samples = ctx.empri_wq.get(empri["empriCode"], []) if empri else []
    if samples:
        tests = defaultdict(dict)
        for r in samples:
            v = num(r.get("value"))
            if v is not None:
                tests[(r.get("sampleDate"), r.get("samplingPoint"))][r["parameter"]] = v
        s.set(
            "surveyTests",
            [{k: v for k, v in {"date": d, "point": pt, "values": vals}.items() if v} for (d, pt), vals in sorted(tests.items(), key=lambda kv: str(kv[0]))],
            "empri-2018",
        )
    return s


def point_of(row):
    lat, lon = num(row.get("lat")), num(row.get("lon"))
    return [lon, lat] if lat is not None and lon is not None else None
