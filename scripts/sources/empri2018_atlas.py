"""
The EMPRI 2018 lake atlas: one sheet per lake (mostly kere), after the database tables in each
Volume II part. The left half of a sheet is a set of "Label : value" fields laid out in columns;
the right half holds a numbered table of issues and conservation strategies, then photos.

parse_atlas() returns one dict per sheet with the fields the database tables do not already
carry, plus the sheet's own EMPRI code, lake name and visit date for linking. Values are kept as printed, except "Not Observed"/"NA"/"Nil" which become empty.
"""

import json
import re

# Every label printed on a sheet, as lowercase words. Labels we do not export still matter:
# they end the value of the label before them.
LABELS = [
    "lake name", "date of visit", "basic information", "other name", "empri code", "maximum depth (m)", "maximum depth",
    "district name", "mi tank reg. no", "mi tank reg. no.", "taluk name", "year of creation", "geographical coordinates",
    "geographical", "coordinates", "hobli name", "year of rejuvenation", "lat.", "lat", "long.", "long", "village name",
    "survey no.", "extent area(a-g)", "extent area (a-g)", "source", "total extent (a-g)", "preservation authority",
    "morphology", "water quality", "hydrology", "elevation(m)", "inlet drain", "waste weir", "sluice gate", "fence",
    "culverts", "check dam", "road", "surrounding area", "temperature (°c)", "ph", "conductivity (µs/cm)",
    "light transparency (m)", "tss (mg/l)", "tss(mg/l)", "tds (mg/l)", "turbidity (ntu)", "do (mg/l)", "bod (mg/l)",
    "cod (mg/l)", "tkn (mg/l)", "tkn(mg/l)", "phosphate (mg/l)", "total coliform (mpn/100ml)", "total coliform",
    "status", "type", "source of water", "upstream water body", "downstream water body", "nature of catchment",
    "um is unable to measure", "nd is for not detectable", "na is not applicable", "date of sampling",
    "biotic data", "socio-economic value", "vegetation cover", "vegetation type", "aquatic flora", "fauna", "amphibian",
    "reptile", "mammals", "drinking water", "washing", "bathing", "livestock management", "irrigation", "fishing",
    "cultural activities", "recreational activity", "others uses", "other uses", "threats",
    "direct point source pollutants", "indirect point source pollutants", "quantity of sewage inflow (cumecs)",
    "encroachment", "soil excavation", "weeds",
]
LABEL_WORDS = sorted({tuple(label.split()) for label in LABELS}, key=len, reverse=True)

# Exported fields: output column -> label.
FIELDS = {
    "atlasMiTankRegNo": "mi tank reg. no",
    "atlasYearCreated": "year of creation",
    "atlasYearRejuvenated": "year of rejuvenation",
    "atlasPreservationAuthority": "preservation authority",
    "atlasTotalExtentText": "total extent (a-g)",
    "atlasSourceOfWater": "source of water",
    "atlasUpstream": "upstream water body",
    "atlasDownstream": "downstream water body",
    "atlasCatchment": "nature of catchment",
    "atlasRoads": "road",
    "atlasDrinkingWater": "drinking water",
    "atlasWashing": "washing",
    "atlasBathing": "bathing",
    "atlasLivestock": "livestock management",
    "atlasIrrigation": "irrigation",
    "atlasFishing": "fishing",
    "atlasCultural": "cultural activities",
    "atlasRecreation": "recreational activity",
    "atlasOtherUses": "others uses",
    "atlasAmphibians": "amphibian",
    "atlasReptiles": "reptile",
    "atlasMammals": "mammals",
    "atlasDirectPollutants": "direct point source pollutants",
    "atlasIndirectPollutants": "indirect point source pollutants",
    "atlasSewageInflowCumecs": "quantity of sewage inflow (cumecs)",
    "atlasEncroachment": "encroachment",
    "atlasSoilExcavation": "soil excavation",
}
ALIASES = {"mi tank reg. no.": "mi tank reg. no", "other uses": "others uses", "total extent (a-g)": "total extent (a-g)"}
ATLAS_COLUMNS = ["atlasCode", "atlasName", *FIELDS, "atlasStrategies", "atlasPage"]
EMPTY = {"not observed", "na", "nil", "no", "-", "nob", ""}


def norm(token):
    return token.lower().rstrip(":").strip()


def split_colons(words):
    """'Area:TV9' -> 'Area:' + 'TV9', so a label glued to its value is still found."""
    out = []
    for w in words:
        parts = re.split(r"(?<=:)(?=[^:\s])", w["text"])
        if len(parts) == 1 or w["text"].startswith(":"):
            out.append(w)
            continue
        width, x = (w["x1"] - w["x0"]) / max(len(w["text"]), 1), w["x0"]
        for part in parts:
            out.append({**w, "text": part, "x0": x, "x1": x + width * len(part)})
            x += width * len(part)
    return out


def lines_of(words, tolerance=4):
    lines = []
    for w in sorted(split_colons(words), key=lambda w: (w["top"], w["x0"])):
        if lines and abs(lines[-1][0] - w["top"]) <= tolerance:
            lines[-1][1].append(w)
        else:
            lines.append([w["top"], [w]])
    return [(top, sorted(ws, key=lambda w: w["x0"])) for top, ws in lines]


def find_labels(lines):
    """Candidate label occurrences: (label, line index, first word index, end word index, x0)."""
    found = []
    for li, (_, ws) in enumerate(lines):
        tokens = [norm(w["text"]) for w in ws]
        i = 0
        while i < len(ws):
            hit = None
            for words in LABEL_WORDS:
                n = len(words)
                chunk = tokens[i:i + n]
                # "body:" and "::Mesh": a colon can stick to either side of a label.
                if len(chunk) == n and all(a == b or a == b.rstrip(".") for a, b in zip(chunk, words)):
                    hit = (" ".join(words), n)
                    break
            if hit:
                found.append((ALIASES.get(hit[0], hit[0]), li, i, i + hit[1], ws[i]["x0"]))
                i += hit[1]
            else:
                i += 1
    return found


def value_words(words):
    """Join value words, dropping the colon that follows a label ("::Mesh", ": Nil")."""
    out = []
    for w in words:
        t = w["text"] if out else w["text"].lstrip(":")
        if t:
            out.append(t)
    return " ".join(out).strip()


SECTION_HEADS = ["basic information", "morphology", "biotic data", "threats"]
# Printed text that ends any value above it in the same column: table headers and footnotes.
STOPS = {"date of sampling", "village name", "survey no.", "extent area(a-g)", "extent area (a-g)", "total extent (a-g)",
         "um is unable to measure", "nd is for not detectable", "na is not applicable", *SECTION_HEADS}


def columns(labels, lines):
    """
    Split the sheet into its four sections and find each section's column starts: the x positions
    where at least two labels line up. Only labels at a column start are real; the same words
    inside a value ("Agricultural encroachment") are not.
    """
    heads = sorted(lines[li][0] for label, li, *_ in labels if label in SECTION_HEADS)
    bands = list(zip(heads, heads[1:] + [10_000]))
    band_of = lambda top: next((b for b in bands if b[0] <= top < b[1]), None)  # noqa: E731
    starts = {}
    for band in bands:
        xs = sorted(x0 for label, li, _, _, x0 in labels if band_of(lines[li][0]) == band and label not in SECTION_HEADS)
        clusters = []
        for x in xs:
            if clusters and x - clusters[-1][-1] <= 14:
                clusters[-1].append(x)
            else:
                clusters.append([x])
        merged = []
        for x in [min(c) for c in clusters if len(c) >= 2]:
            if not merged or x - merged[-1] > 40:  # real columns are 100 pt or more apart
                merged.append(x)
        starts[band] = merged
    return band_of, starts


def read_fields(lines, half):
    candidates = find_labels(lines)
    band_of, starts = columns(candidates, lines)
    labels = []
    for label, li, wi, end, x0 in candidates:
        band = band_of(lines[li][0])
        if band and any(abs(x0 - s) <= 14 for s in starts[band]):
            labels.append((label, li, wi, end, x0, band))
    label_words = {(li, k) for _, li, wi, end, _, _ in labels for k in range(wi, end)}
    label_at = {(li, wi) for _, li, wi, _, _, _ in labels}
    label_at |= {(li, wi) for label, li, wi, _, _ in candidates if label in STOPS}
    values = {}
    for label, li, wi, end, x0, band in labels:
        cols = starts[band]
        left = max([s for s in cols if s <= x0 + 14] or [x0])
        right = min([s for s in cols if s > left + 14] + [half + 15])
        ws = lines[li][1]
        same = []
        for k in range(end, len(ws)):
            if (li, k) in label_at or ws[k]["x0"] >= right:
                break
            same.append(ws[k])
        text = [value_words(same)]
        last = lines[li][0]
        for lj in range(li + 1, len(lines)):
            top, lws = lines[lj]
            if top >= band[1] or top - last > 60:
                break
            in_col = [(k, w) for k, w in enumerate(lws) if left - 8 <= w["x0"] < right]
            if any((lj, k) in label_at for k, _ in in_col):
                break
            words = [w for k, w in in_col if (lj, k) not in label_words]
            if words:
                text.append(value_words(words))
                last = top
        values.setdefault(label, re.sub(r"\s+", " ", " ".join(t for t in text if t)).strip(" :"))
    return values


def read_strategies(page, half):
    """The numbered 'Issues | Strategies' table on the right half of the sheet."""
    rows = []
    for table in page.crop((half, 0, page.width, page.height)).extract_tables():
        for row in table:
            cells = [re.sub(r"\s+", " ", c).strip() for c in row if c and c.strip()]
            if len(cells) >= 2 and re.fullmatch(r"\d{1,2}\.?", cells[0]):
                issue, strategy = cells[1], " ".join(cells[2:])
                rows.append(f"{issue}: {strategy}" if strategy else issue)
    return rows


def clean_value(v):
    v = re.sub(r"\s+", " ", v or "").strip(" :,")
    v = re.split(r"\s+[a-z][\w ]{0,24}\s:\s", v, maxsplit=1)[0]  # ran into a neighbouring label ("b athing : ...")
    v = re.sub(r"\s*Bengaluru Lakes\b.*$", "", v, flags=re.I)  # page footer
    # Footnotes and the sampling date printed under the hydrology column.
    v = re.sub(r"\s+((UM|ND|NA|NW)\s+(is\s|unable).*|date of sampling.*|\d{1,2}\.\d{1,2}\.\d{2,4})$", "", v, flags=re.I)
    return None if v.lower().rstrip(".") in EMPTY else v


def parse_sheet(page):
    half = page.width / 2
    words = page.extract_words()
    left = lines_of([w for w in words if w["x1"] <= half + 15])
    text = " ".join(w["text"] for _, ws in left for w in ws)
    head = re.search(r"Lake\s*Name\s*:?\s*(.+?)\s+Date\s*of\s*Visit\s*:?\s*([\d.]+)", text)
    if not head or "BASIC" not in text:
        return None
    code = re.search(r"EMPRI\s*Code\s*:?\s*(BU\S+)", text)
    values = read_fields(left, half)
    fields = {
        "atlasCode": code.group(1) if code else None,
        "atlasName": head.group(1).strip(),
        "atlasVisitDate": head.group(2).strip("."),
        **{col: clean_value(values.get(label)) for col, label in FIELDS.items()},
    }
    # The survey-number table has no label column; its total is one line of text.
    total = re.search(r"Total\s+Extent\s*\(A-G\)\s*:?\s*(≈?\s*[\d.]+)", text)
    fields["atlasTotalExtentText"] = total.group(1).replace(" ", "") if total else None
    fields["atlasStrategies"] = read_strategies(page, half)
    fields["atlasPage"] = page.page_number
    return fields


def parse_atlas(pdf_path, cache):
    """All atlas sheets of one Volume II part, in page order."""
    if cache.exists():
        return json.loads(cache.read_text())
    import pdfplumber

    out = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            head = (page.extract_text() or "")[:400]
            if "Lake Name" in head and "BASIC" in head:
                fields = parse_sheet(page)
                if fields:
                    out.append(fields)
    cache.write_text(json.dumps(out, ensure_ascii=False))
    return out
