"""
The historic map sheets used by historic_maps.py, with what is needed to read each one.

bounds      west, south, east, north of the neatline, degrees on the sheet's own datum
cornersPx   rough neatline corners in the scan (NW, NE, SE, SW), picked by eye once;
            the graticule tracer refines them
graticuleDeg spacing of the printed graticule lines
water       segmentation parameters for historic_maps_water.py
align       alignment parameters for historic_maps_align.py
showsAllWater false when the sheet leaves some water undrawn, so absence means nothing
reject      reason a sheet is left out after review, when its alignment report passes but
            the named check lakes on it do not
minAreaM2   smallest water body kept: below this the sheet's symbols (wells, stream
            beads, marsh dashes) cannot be told from small tanks
"""

COMMONS = "https://commons.wikimedia.org/wiki/File:"
UPLOAD = "https://upload.wikimedia.org/wikipedia/commons/"

SOI_CREDIT = "Survey of India map, public domain, via Wikimedia Commons"
AMS_CREDIT = "U.S. Army Map Service map, public domain, via Wikimedia Commons"

# One-inch and half-inch coloured Survey of India sheets: blue water, dot-screen tank beds. Values are in scan pixels at about 4 m (one-inch) per pixel.
ONE_INCH_WATER = {
    # Water is light blue; hill form lines and a rubber stamp on 57 G/12 are darker blue.
    "blueHue": [92, 118],
    "blueSatMin": 35,
    "blueValMin": 190,
    "darkBlueHaloPx": 5,
    "openPx": 2,
    "closePx": 5,
    "maxHolePx": 20000,
    # Tank-bed dots are neutral grey; hill shading is a finer, fainter, bluish halftone.
    "dotScreen": True,
    "dotDarkMax": 190,
    "dotGreyMax": 40,
    "dotArea": [2, 16, 6],
    "dotWindow": 25,
    "dotPaperMin": 210,
    "dotMinCount": 6,
}
HALF_INCH_WATER = {
    **ONE_INCH_WATER,
    "closePx": 4,
    "maxHolePx": 10000,
    "dotArea": [2, 12, 5],
    "dotWindow": 21,
}
# Quarter-inch sheets are faded JPEG scans: tanks are a pale halftone found by blue tint.
QUARTER_INCH_WATER = {"tintMin": -20, "tintBlur": 1.5, "openPx": 4, "closePx": 1, "maxHolePx": 200}
# 1945 black-and-white reprint: tanks are an irregular dot stipple.
STIPPLE_WATER = {
    "dotDarkMax": 210,
    "dotArea": [2, 25, 6],
    "dotWindow": 51,
    "dotPaperMin": 190,
    "dotMinCount": 6,
    "dotNeighbours": [15, 4],
    "openPx": 6,
    "closePx": 8,
    "maxHolePx": 40000,
}
AMS_WATER = {
    "blueHue": [90, 125],
    "blueSatMin": 20,
    "blueValMin": 100,
    "densityWindow": 9,
    "densityMin": 0.45,
    "openPx": 2,
    "closePx": 2,
    "maxHolePx": 200,
    "blankYellow": {"hue": [15, 30], "satMin": 120, "valMin": 170, "closePx": 5, "openPx": 3},
}

ALIGN_ONE_INCH = {
    "alignResM": 10,
    "maxShiftM": 1500,
    "localShiftM": 300,
    "minControlLakeM2": 20000,
    "minControlOverlap": 0.3,
}
ALIGN_HALF_INCH = {**ALIGN_ONE_INCH, "alignResM": 15, "minControlLakeM2": 40000}
ALIGN_SMALL_SCALE = {
    "alignResM": 25,
    "maxShiftM": 1500,
    "localShiftM": 400,
    "minControlLakeM2": 100000,
    "minControlOverlap": 0.3,
}


def commons(file_title, path):
    return {"url": COMMONS + file_title, "download": UPLOAD + path}


SHEETS = [
    {
        "key": "soi-57g-sw-1918",
        "title": "Survey of India half-inch sheet 57 G/SW (Mysore: Bangalore, Kolar & Tumkur districts), "
        "surveyed 1912-15, published 1918",
        "publisher": "Survey of India",
        "license": "Public domain",
        "credit": SOI_CREDIT,
        **commons("Survey_of_India_57_G_SW.png", "1/13/Survey_of_India_57_G_SW.png"),
        "file": "Survey_of_India_57_G_SW.png",
        "sourceKey": "soi-57g-sw-1918",
        "year": 1918,
        "scale": 126720,
        "bounds": (77.0, 13.0, 77.5, 13.5),
        "projection": "poly",
        "cornersPx": [(432, 659), (7136, 640), (7140, 7545), (455, 7560)],
        "graticuleDeg": 5 / 60,
        "style": "soi-colour",
        "water": HALF_INCH_WATER,
        "align": ALIGN_HALF_INCH,
        "minAreaM2": 10000,
        "simplifyPx": 0.75,
    },
    {
        "key": "soi-57h-1923",
        "title": "Survey of India quarter-inch sheet 57 H Bangalore (Madras & Mysore), surveyed 1907-15, "
        "published 1923",
        "publisher": "Survey of India",
        "license": "Public domain",
        "credit": SOI_CREDIT,
        **commons("57_H_Bangalore_(1923).jpg", "6/60/57_H_Bangalore_%281923%29.jpg"),
        "file": "57_H_Bangalore_%281923%29.jpg",
        "sourceKey": "soi-57h-1923",
        "year": 1923,
        "scale": 253440,
        "bounds": (77.0, 12.0, 78.0, 13.0),
        "projection": "poly",
        "cornersPx": [(426, 694), (5389, 715), (5381, 5854), (389, 5830)],
        "graticuleDeg": 0.25,
        "order": 3,
        "style": "soi-colour",
        "water": QUARTER_INCH_WATER,
        "align": ALIGN_SMALL_SCALE,
        "minAreaM2": 30000,
        "simplifyPx": 0.5,
    },
    {
        "key": "soi-57g12-1927",
        "title": "Survey of India one-inch sheet 57 G/12 (Mysore: Bangalore District), third (revised) edition, "
        "surveyed 1912-13 and 1924-25, published 1927",
        "publisher": "Survey of India",
        "license": "Public domain",
        "credit": SOI_CREDIT,
        **commons("Survey_of_India_57_G_12.png", "1/14/Survey_of_India_57_G_12.png"),
        "file": "Survey_of_India_57_G_12.png",
        "sourceKey": "soi-57g12-1927",
        "year": 1927,
        "scale": 63360,
        "bounds": (77.5, 13.0, 77.75, 13.25),
        "projection": "poly",
        "cornersPx": [(521, 686), (7218, 667), (7226, 7500), (519, 7522)],
        "graticuleDeg": 5 / 60,
        "style": "soi-colour",
        "water": ONE_INCH_WATER,
        "align": ALIGN_ONE_INCH,
        "minAreaM2": 4000,
        "simplifyPx": 1.0,
    },
    {
        "key": "soi-57g-1929",
        "title": "Survey of India quarter-inch sheet 57 G Tumkur (Mysore), published 1929",
        "publisher": "Survey of India",
        "license": "Public domain",
        "credit": SOI_CREDIT,
        **commons("57_G_Tumkur_(1929).jpg", "4/46/57_G_Tumkur_%281929%29.jpg"),
        "file": "57_G_Tumkur_%281929%29.jpg",
        "sourceKey": "soi-57g-1929",
        "year": 1929,
        "scale": 253440,
        "bounds": (77.0, 13.0, 78.0, 14.0),
        "projection": "poly",
        "reject": "quarter-inch: after correction Hebbal, Yelahanka and Hesaraghatta are still 120-250 m off, "
        "only 13 lakes to check against, and only tanks holding water are drawn",
        "cornersPx": [(407, 544), (5348, 515), (5395, 5654), (455, 5685)],
        "graticuleDeg": 0.25,
        "order": 3,
        "style": "soi-colour",
        "water": QUARTER_INCH_WATER,
        "align": ALIGN_SMALL_SCALE,
        "minAreaM2": 30000,
        "simplifyPx": 0.5,
    },
    {
        "key": "soi-57h9-1945",
        "title": "Survey of India one-inch sheet 57 H/9 (Madras & Mysore: Bangalore District), fifth edition, "
        "surveyed 1912-13 and 1924-25, revised 1943, published 1945",
        "publisher": "Survey of India",
        "license": "Public domain",
        "credit": SOI_CREDIT,
        **commons("Survey_of_India_57_H_9.png", "7/7b/Survey_of_India_57_H_9.png"),
        "file": "Survey_of_India_57_H_9.png",
        "sourceKey": "soi-57h9-1945",
        "year": 1945,
        "scale": 63360,
        "bounds": (77.5, 12.75, 77.75, 13.0),
        "projection": "poly",
        # The neatline is overprinted by a purple yard grid and has no interior graticule.
        "cornersPx": [(458, 1190), (7185, 1200), (7162, 8065), (429, 8067)],
        "graticuleDeg": 0,
        "traceLines": False,
        # Black-plate-only reprint: open water (the blue plate) is printed blank, so only
        # tank beds show and a tank missing here may still have been full of water.
        "showsAllWater": False,
        "style": "soi-stipple",
        "water": STIPPLE_WATER,
        "align": ALIGN_ONE_INCH,
        "minAreaM2": 20000,
        "simplifyPx": 1.5,
    },
]

AMS = [
    ("ND 43-12", "Tumkur", "6/6c", (76.0, 13.0, 77.5, 14.0), [(317, 250), (4627, 252), (4637, 3200), (315, 3200)]),
    ("ND 43-16", "Mysore", "3/31", (76.0, 12.0, 77.5, 13.0), [(330, 280), (4646, 285), (4648, 3221), (322, 3219)]),
    ("ND 44-9", "Kolar", "a/a6", (77.5, 13.0, 79.0, 14.0), [(368, 257), (4648, 249), (4660, 3190), (362, 3196)]),
    ("ND 44-13", "Bangalore", "0/05", (77.5, 12.0, 79.0, 13.0), [(465, 275), (4594, 275), (4600, 3092), (455, 3090)]),
]
for code, place, hashdir, bounds, corners in AMS:
    name = f"Map_India_and_Pakistan_1-250,000_Tile_{code.replace(' ', '_')}_{place}.jpg"
    quoted = name.replace(",", "%2C")
    SHEETS.append(
        {
            "key": f"ams-{code.lower().replace(' ', '')}-1955",
            "title": f"U.S. Army Map Service, India and Pakistan 1:250,000, series U502, sheet {code} {place}, "
            "edition 1-AMS, compiled 1954 from Survey of India one-inch maps of 1945-46",
            "publisher": "U.S. Army Map Service",
            "license": "Public domain (U.S. Government work)",
            "credit": AMS_CREDIT,
            "url": COMMONS + name,
            "download": f"{UPLOAD}{hashdir}/{quoted}",
            "file": quoted,
            "sourceKey": f"ams-{code.lower().replace(' ', '')}-1955",
            "year": 1955,
            "scale": 250000,
            "bounds": bounds,
            "projection": "tm",
            "cornersPx": corners,
            "graticuleDeg": 0,
            "style": "ams",
            "water": AMS_WATER,
            "align": ALIGN_SMALL_SCALE,
            "minAreaM2": 50000,
            "simplifyPx": 0.5,
        }
    )
