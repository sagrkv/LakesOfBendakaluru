#!/usr/bin/env python3
"""
JRC Global Surface Water: how often each lake has held water since 1984.

Summary layers come from version 1.5 (1984-2024). The year-by-year classification is only
published as files up to 2021 (version 1.4); 2022-2024 is on Google Earth Engine only.

Pixels (30 m) count for a lake when their centre is inside the outline. Lakes smaller than about
1 ha have only a handful of pixels, so they are flagged lowConfidence.
Floating weed reads as land, so weed-choked lakes such as Bellandur show low occurrence.
These values are not corrected for that.

Usage: .venv/bin/python scripts/sources/jrc_water.py [--input lakes.geojson --key atreeFid]
Output: data/sources/jrc_water.csv, data/sources/jrc_yearly.csv
"""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE, SOURCES, write_csv, write_sources  # noqa: E402

from _lake_input import Grid, cache_window, lakes_bounds, load_lakes, parse_args, pixel_area_m2  # noqa: E402

NAME = "jrc_water"
AGG_URL = (
    "https://s3.waw4-1.cloudferro.com/swift/v1/global-surface-water/download2024/"
    "Aggregated/VER1-5/{layer}/{layer}_70E_20N_v1_5_2024.tif"
)
YEARLY_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GSWE/YearlyClassification/LATEST/tiles/"
    "yearlyClassification{year}/yearlyClassification{year}{sep}0000240000-0001000000.tif"
)
# 2021 names its tiles with "_", earlier years with "-".
YEARLY_SEP = {2021: "_"}
LAYERS = ["occurrence", "change", "seasonality", "recurrence", "transitions", "extent"]
YEARS = range(1984, 2022)
KEY_AGG, KEY_YEARLY = "jrc-gsw-1-5", "jrc-gsw-1-4-yearly"

# Transition classes, first year vs last year of the record.
TRANSITIONS = {
    1: "pctPermanent",
    2: "pctNewPermanent",
    3: "pctLostPermanent",
    4: "pctSeasonal",
    5: "pctNewSeasonal",
    6: "pctLostSeasonal",
    7: "pctSeasonalToPermanent",
    8: "pctPermanentToSeasonal",
    9: "pctEphemeral",  # ephemeral permanent
    10: "pctEphemeral",  # ephemeral seasonal
}
MIN_PIXELS = 13  # about 1 ha of 30 m pixels

COLUMNS = [
    "key",
    "pixelCount",
    "lowConfidence",
    "occurrenceMean",
    "occurrenceMedian",
    "pctEverWater",
    "pctNeverWater",
    "pctPermanent",
    "pctSeasonal",
    "pctSeasonalToPermanent",
    "pctPermanentToSeasonal",
    "pctLostPermanent",
    "pctLostSeasonal",
    "pctNewPermanent",
    "pctNewSeasonal",
    "pctEphemeral",
    "seasonalityMeanMonths",
    "recurrenceMean",
    "changeMean",
    "firstYearWithWater",
    "lastYearWithWater",
    "source",
]
YEARLY_COLUMNS = ["key", "year", "waterPermanentM2", "waterSeasonalM2", "noDataM2", "observedM2", "source"]


def r1(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 1)


def summarise(pix):
    """pix: dict layer -> values for one lake's pixels."""
    n = len(pix["occurrence"])
    occ = pix["occurrence"][pix["occurrence"] <= 100].astype(float)
    ever = pix["extent"] == 1
    trans = pix["transitions"]
    row = {
        "occurrenceMean": r1(occ.mean()) if occ.size else None,
        "occurrenceMedian": r1(np.median(occ)) if occ.size else None,
        "pctEverWater": r1(100 * ever.mean()),
        "pctNeverWater": r1(100 * (1 - ever.mean())),
    }
    for col in set(TRANSITIONS.values()):
        classes = [c for c, name in TRANSITIONS.items() if name == col]
        row[col] = r1(100 * np.isin(trans, classes).mean())
    seas = pix["seasonality"][pix["seasonality"] <= 12].astype(float)
    row["seasonalityMeanMonths"] = r1(seas.mean()) if seas.size else None
    rec = pix["recurrence"][ever & (pix["recurrence"] <= 100)].astype(float)
    row["recurrenceMean"] = r1(rec.mean()) if rec.size else None
    chg = pix["change"][pix["change"] <= 200].astype(float) - 100
    row["changeMean"] = r1(chg.mean()) if chg.size else None
    row["pixelCount"] = n
    return row


def build():
    args = parse_args(__doc__.split("\n")[1])
    lakes = load_lakes(args)
    bounds = lakes_bounds(lakes, margin_deg=0.01)
    cache = CACHE / NAME

    grids = {}
    for layer in LAYERS:
        path = cache_window(AGG_URL.format(layer=layer), cache / f"{layer}.tif", bounds)
        grids[layer] = Grid.open(path)
    base = grids["occurrence"]
    for layer, grid in grids.items():
        assert grid.transform.almost_equals(base.transform, 1e-9) and grid.data.shape == base.data.shape, layer

    masks = {}
    rows = []
    for lake in lakes:
        r, c, inside, centre = base.mask(lake["geom"])
        ever = grids["extent"].data[r, c][inside] == 1
        masks[lake["key"]] = (r, c, inside, ever, lake["geom"].centroid.y)
        pix = {layer: grids[layer].data[r, c][inside] for layer in LAYERS}
        row = {"key": lake["key"], "source": KEY_AGG} | summarise(pix)
        row["lowConfidence"] = row["pixelCount"] < MIN_PIXELS or not centre or lake["isPoint"]
        rows.append(row)

    yearly = []
    water_years = {lake["key"]: [] for lake in lakes}
    for year in YEARS:
        path = cache_window(
            YEARLY_URL.format(year=year, sep=YEARLY_SEP.get(year, "-")), cache / f"yearly{year}.tif", bounds
        )
        grid = Grid.open(path)
        assert grid.transform.almost_equals(base.transform, 1e-9) and grid.data.shape == base.data.shape, year
        for key, (r, c, inside, ever, lat) in masks.items():
            v = grid.data[r, c][inside]
            px = pixel_area_m2(lat, *grid.res)
            # The yearly files also write 0 for pixels that were never water in any year.
            # Those are land whatever the year, so only 0 on a pixel that was water at some time is missing data.
            permanent, seasonal, nodata = int((v == 3).sum()), int((v == 2).sum()), int(((v == 0) & ever).sum())
            yearly.append(
                {
                    "key": key,
                    "year": year,
                    "waterPermanentM2": round(permanent * px),
                    "waterSeasonalM2": round(seasonal * px),
                    "noDataM2": round(nodata * px),
                    "observedM2": round((v.size - nodata) * px),
                    "source": KEY_YEARLY,
                }
            )
            # A year counts as "with water" when at least 5% of the lake's pixels (min. 1) were water.
            if permanent + seasonal >= max(1, math.ceil(0.05 * v.size)):
                water_years[key].append(year)

    for row in rows:
        years = water_years[row["key"]]
        row["firstYearWithWater"] = min(years) if years else None
        row["lastYearWithWater"] = max(years) if years else None

    write_csv(SOURCES / f"{NAME}.csv", rows, COLUMNS)
    write_csv(SOURCES / "jrc_yearly.csv", yearly, YEARLY_COLUMNS)
    credit = "Source: EC JRC/Google (Pekel et al. 2016, Nature 540, 418-422)"
    write_sources(
        NAME,
        [
            {
                "key": KEY_AGG,
                "title": "Global Surface Water v1.5, 1984-2024 (occurrence, change, seasonality, recurrence, transitions, extent)",
                "publisher": "European Commission Joint Research Centre / Google",
                "url": "https://global-surface-water.appspot.com/download",
                "license": "CC BY 4.0",
                "credit": credit,
                "asOf": "2024",
                "retrieved": "2026-09-11",
            },
            {
                "key": KEY_YEARLY,
                "title": "Global Surface Water v1.4 yearly water classification history, 1984-2021",
                "publisher": "European Commission Joint Research Centre / Google",
                "url": "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GSWE/YearlyClassification/LATEST/",
                "license": "CC BY 4.0",
                "credit": credit,
                "asOf": "2021",
                "retrieved": "2026-09-11",
            },
        ],
    )
    print(f"{NAME}: {len(rows)} lakes, {len(yearly)} yearly rows")


if __name__ == "__main__":
    build()
