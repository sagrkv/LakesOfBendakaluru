"""
The historic map sheets used by historic_maps.py, with what is needed to read each one.

year        the year the sheet was published
edition     the map year a lake record uses (onMap<edition>): sheets of one survey
            campaign printed over several years share it, e.g. the 1914-1917 one-inch
            sheets are edition 1914 and the 1973-1980 metric sheets are edition 1975.
            The sheet's own year stays in its source key and citation.
bounds      west, south, east, north of the neatline, degrees on the sheet's own datum
cornersPx   rough neatline corners in the scan (NW, NE, SE, SW), found once from the
            printed graticule lattice and checked by eye; the graticule tracer refines them
searchPx    how far from the predicted line the tracer looks (default 12)
graticuleDeg spacing of the printed graticule lines
water       segmentation parameters for historic_maps_water.py
align       alignment parameters for historic_maps_align.py
showsAllWater false when the sheet leaves some water undrawn, so absence means nothing
reject      reason a sheet is left out after review, when its alignment report passes but
            the named check lakes on it do not
minAreaM2   smallest water body kept: below this the sheet's symbols (wells, stream
            beads, marsh dashes) cannot be told from small tanks
"""

from urllib.parse import quote

COMMONS = "https://commons.wikimedia.org/wiki/File:"
UPLOAD = "https://upload.wikimedia.org/wikipedia/commons/"
ZENODO_RECORD = "https://zenodo.org/records/8388121"
ZENODO_API = "https://zenodo.org/api/records/8388121"

SOI_CREDIT = "Survey of India map, public domain, via Wikimedia Commons"
AMS_CREDIT = "U.S. Army Map Service map, public domain, via Wikimedia Commons"
ZENODO_CREDIT = "Survey of India map, scanned collection by John Brown, CC BY 4.0, via Zenodo"

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
# 1914-1917 one-inch sheets, JPEG scans at about 5 m per pixel. Water is a pale grey-blue
# (saturation 10-40) that no fixed hue box separates from the paper, whose own tint differs
# from sheet to sheet. Blue minus red does: land is well below zero, water at or above it,
# with an empty gap between. The threshold is set in that gap for each sheet. Tank beds
# carry no dot screen on these prints, so only water is traced.
# Streams and the Arkavathi are drawn in the same blue up to 10 px wide: a 5 px opening removes
# them and keeps tanks down to the smallest size kept.
SOI_1914_WATER = {
    "tintMin": [-16, 8],
    "tintBlur": 2.0,
    "tintValMin": 150,
    "openPx": 5,
    "closePx": 4,
    "maxHolePx": 15000,
    # Wider river stretches and bends survive the opening. Checked on the scans, river pieces were
    # 39-54 m wide on average with roundness 0.36-0.72, tanks 49-110 m with 0.39-0.91; this
    # drops every river piece checked and 1 tank in 7.
    "streamShape": {"widthM": 56, "maxCompactness": 0.75},
}
# 1973-1980 first metric (1:50,000) sheets: water a saturated mid blue; dry tank beds a
# regular black dot screen, often on pale paper that is darker than the old one-inch paper
# (about 160 in the darkest channel between dots). The screen is 8 px on most prints and
# up to 12 px with fat dots on others (57 G/4), so the paper is judged over 9 px, dots are
# counted over 35 px, and beds must survive a 6 px opening that removes small clusters of
# dotted symbols. Wells, blue tree symbols and stream lines are removed by the blue
# opening; dotted boundary lines by the neighbour rule.
SOI_METRIC_WATER = {
    "blueHue": [88, 115],
    "blueSatMin": 50,
    "blueValMin": 120,
    "openPx": 3,
    "closePx": 5,
    "maxHolePx": 20000,
    "dotScreen": True,
    "dotDarkMax": 150,
    "dotGreyMax": 70,
    "dotArea": [3, 20, 6],
    "dotWindow": 35,
    "dotPaperMin": 120,
    "dotPaperPx": 9,
    "dotMinCount": 8,
    # Field boundaries are rows of dots: a bed dot needs 4 neighbours within 16 px spread in two directions.
    "dotNeighbours": [16, 4, 0.35],
    "dotOpenPx": 6,
    # Dark green plantation and tree dots pass as grey after JPEG compression.
    "dotGreenMax": 12,
    # Dotted field enclosures on 57 G/12 trace as beds up to about 50,000 m2 and no pixel rule
    # tried (fill share, neighbour spread, green cast) tells them apart, so dot-only shapes
    # below this size are low confidence and never become new lakes.
    "dotOnlyMinAreaM2": 50000,
    # Rivers are printed solid blue up to 60 m wide and survive the opening. Checked on the scans,
    # river pieces were 23-38 m wide on average with roundness 0.03-0.23; tanks 85 m and over.
    "streamShape": {"widthM": 45, "maxCompactness": 0.3},
}
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


def one_inch_bounds(block, number):
    """
    Neatline of a 15-minute sheet of degree block 57 G (13-14 N) or 57 H (12-13 N), 77-78 E.
    Sheets 1-16 run down columns from the west: 1-4 in the first, 13-16 in the last.
    """
    column, row = (number - 1) // 4, (number - 1) % 4
    west = 77.0 + 0.25 * column
    north = (14.0 if block == "G" else 13.0) - 0.25 * row
    return (west, north - 0.25, west + 0.25, north)


# Survey of India sheets from the Zenodo collection "Block 57--63k scale--Survey of India Maps".
# (block, number, district on the sheet, year published, corners, extra settings)
ZENODO_1914 = [
    ("G", 4, "Bangalore", 1916, [(374, 458), (5399, 448), (5397, 5599), (373, 5609)], {}),
    # Interior graticule too faint to find: corners read off the neatline at 1.5x.
    ("G", 8, "Bangalore", 1914, [(300, 440), (5310, 435), (5310, 5552), (296, 5552)], {"searchPx": 20}),
    ("G", 16, "Bangalore", 1914, [(285, 514), (5304, 500), (5307, 5630), (296, 5630)], {"searchPx": 20}),
    ("H", 5, "Bangalore", 1914, [(261, 512), (5285, 499), (5289, 5622), (265, 5634)], {}),
    ("H", 6, "Bangalore", 1917, [(525, 363), (5550, 373), (5537, 5502), (512, 5492)], {}),
    ("H", 7, "Bangalore", 1914, [(522, 495), (5557, 489), (5561, 5632), (526, 5638)], {}),
    ("H", 10, "Bangalore", 1915, [(467, 405), (5499, 405), (5495, 5547), (463, 5547)], {}),
]
ZENODO_1975 = [
    ("G", 4, "Bangalore", 1973, [(388, 692), (6773, 704), (6754, 7247), (368, 7235)], {}),
    ("G", 7, "Bangalore", 1975, [(340, 785), (6718, 782), (6721, 7328), (343, 7332)], {}),
    ("G", 8, "Bangalore", 1974, [(365, 752), (6756, 745), (6764, 7272), (374, 7279)], {}),
    ("G", 11, "Kolar", 1975, [(411, 731), (6794, 756), (6773, 7306), (389, 7281)], {}),
    # The city sheets fill cultivated land yellow and draw dotted field and village enclosures
    # that trace as beds up to about 150,000 m2 (checked on the scans near Begihalli and Jakkur).
    ("G", 12, "Bangalore", 1978, [(334, 737), (6727, 737), (6733, 7263), (340, 7263)], {"dotOnlyMinAreaM2": 150000}),
    # A fold breaks the southern lines: corners extrapolated from the lines that were found.
    ("G", 16, "Bangalore", 1974, [(318, 753), (6701, 740), (6714, 7292), (331, 7305)], {"searchPx": 20}),
    ("H", 5, "Bangalore", 1973, [(323, 738), (6734, 763), (6709, 7293), (298, 7268)], {}),
    ("H", 6, "Bangalore", 1973, [(376, 745), (6792, 746), (6795, 7286), (379, 7285)], {}),
    ("H", 7, "Bangalore", 1979, [(330, 748), (6765, 738), (6766, 7274), (330, 7284)], {}),
    ("H", 9, "Bangalore", 1980, [(417, 692), (6830, 638), (6878, 7172), (465, 7225)], {"dotOnlyMinAreaM2": 150000}),
    ("H", 10, "Bangalore", 1973, [(431, 724), (6823, 731), (6815, 7272), (423, 7264)], {}),
    ("H", 13, "Kolar", 1973, [(324, 796), (6722, 769), (6747, 7312), (349, 7339)], {}),
]

for edition, sheets in ((1914, ZENODO_1914), (1975, ZENODO_1975)):
    for block, number, district, year, corners, extra in sheets:
        file = f"57 {block}]{number:02d} {district} District ({year}).jpg"
        key = f"soi-57{block.lower()}{number}-{year}"
        title = (
            f"Survey of India one-inch sheet 57 {block}/{number} (Mysore: {district} District), published {year}"
            if edition == 1914
            else f"Survey of India 1:50,000 sheet 57 {block}/{number} (Karnataka: {district} District), "
            f"first metric edition, published {year}"
        )
        SHEETS.append(
            {
                "key": key,
                "title": title,
                "publisher": "Survey of India",
                "license": "CC BY 4.0",
                "credit": ZENODO_CREDIT,
                "url": f"{ZENODO_RECORD}/files/{quote(file)}",
                "download": f"{ZENODO_API}/files/{quote(file)}/content",
                "retrieved": "2026-09-14",
                "file": file,
                "sourceKey": key,
                "year": year,
                "edition": edition,
                "scale": 63360 if edition == 1914 else 50000,
                "bounds": one_inch_bounds(block, number),
                "projection": "poly",
                "cornersPx": corners,
                "graticuleDeg": 5 / 60,
                "style": "soi-colour",
                "water": SOI_1914_WATER if edition == 1914 else SOI_METRIC_WATER,
                "align": ALIGN_ONE_INCH,
                # On the metric sheets a dot-bed shape under 8,000 m2 was more often a cluster of
                # symbols than a tank when checked against the scans.
                "minAreaM2": 5000 if edition == 1914 else 8000,
                "simplifyPx": 1.0,
                **extra,
            }
        )

for sheet in SHEETS:
    sheet.setdefault("edition", sheet["year"])
