"""
Table reader for the KSPCB "Water Quality Data of Bengaluru Lakes" monthly PDFs.

The PDFs are Excel sheets printed to PDF. Their layout drifts from month to month:
columns come and go, headers wrap, and text often spills over cell borders.
parse() returns the report title and one dict per printed row, keyed by the
column vocabulary below, with every cell as the raw printed text.

Two layouts exist:
  - ruled tables (every month but August 2023): cells come from the drawn cell borders,
    and each character is placed in the cell that holds its centre
  - an unruled table (August 2023): rows are anchored on the station code and
    columns come from fixed x positions measured on that PDF
"""

import bisect
import re
from collections import Counter

import pdfplumber
from pdfplumber.utils import extract_text

# Parameter vocabulary: key -> unit. Keys are the `parameter` values in kspcb_readings.csv.
PARAMETERS = {
    "temperature": "degC",
    "dissolvedOxygen": "mg/L",
    "ph": "",
    "conductivity": "uS/cm",
    "bod": "mg/L",
    "cod": "mg/L",
    "nitrate": "mg/L as N",
    "nitrite": "mg/L as N",
    "fecalColiform": "MPN/100mL",
    "totalColiform": "MPN/100mL",
    "fecalStreptococci": "MPN/100mL",
    "carbonate": "mg/L",
    "bicarbonate": "mg/L",
    # Some months label turbidity "(mg/L)"; the method and the values are NTU.
    "turbidity": "NTU",
    "phenolphthaleinAlkalinity": "mg/L as CaCO3",
    "totalAlkalinity": "mg/L as CaCO3",
    "chloride": "mg/L",
    "totalKjeldahlNitrogen": "mg/L as N",
    "ammoniacalNitrogen": "mg/L as N",
    "freeAmmonia": "mg/L as N",
    "totalHardness": "mg/L as CaCO3",
    "calciumHardness": "mg/L as CaCO3",
    "calcium": "mg/L",
    "magnesiumHardness": "mg/L as CaCO3",
    "magnesium": "mg/L",
    "sulphate": "mg/L",
    "sodium": "mg/L",
    "sodiumPercent": "%",
    "sar": "",
    "potassium": "mg/L",
    "tds": "mg/L",
    "tss": "mg/L",
    # "Phosphate" and, from 2026, "Total Phosphate" are the same column.
    "phosphate": "mg/L",
    "orthoPhosphate": "mg/L",
    "boron": "mg/L",
    "fluoride": "mg/L",
    "cadmium": "mg/L",
    "copper": "mg/L",
    "lead": "mg/L",
    "chromium": "mg/L",
    "nickel": "mg/L",
    "zinc": "mg/L",
    "iron": "mg/L",
    "manganese": "mg/L",
    "saprobityIndex": "",
    "diversityIndex": "",
}

# Non-parameter columns.
META = ("serial", "code", "sampled", "name", "lat", "lon", "useClass")

# (key, test on the header squashed to lowercase letters and digits). First match wins, so order matters.
HEADER_RULES = [
    ("serial", lambda n: re.search(r"sl\.?no|^$", n) is not None),
    ("code", lambda n: "code" in n),
    ("sampled", lambda n: "sampling" in n or "samplin" in n),
    ("name", lambda n: "monitoring" in n),
    ("lat", lambda n: "latitude" in n),
    ("lon", lambda n: "longitude" in n),
    ("useClass", lambda n: "usebased" in n or "class" in n),
    ("temperature", lambda n: "temp" in n),
    ("tds", lambda n: "dissolvedsolid" in n or "dissolvsolid" in n),
    ("tss", lambda n: "suspend" in n),
    ("dissolvedOxygen", lambda n: "dissolv" in n),
    ("ph", lambda n: n == "ph"),
    ("conductivity", lambda n: "conduct" in n),
    ("bod", lambda n: n.startswith("bod")),
    ("cod", lambda n: re.search(r"cod(mgl)?$", n) is not None),
    ("nitrite", lambda n: "nitrite" in n),
    ("nitrate", lambda n: "nitrate" in n),
    ("fecalStreptococci", lambda n: "strepto" in n),
    ("fecalColiform", lambda n: "fecal" in n),
    ("totalColiform", lambda n: "coli" in n),
    ("bicarbonate", lambda n: "bicarb" in n),
    ("carbonate", lambda n: "carbo" in n),
    ("turbidity", lambda n: "turbid" in n),
    ("phenolphthaleinAlkalinity", lambda n: "phenol" in n),
    ("totalAlkalinity", lambda n: "alkalin" in n),
    ("chloride", lambda n: "chlorid" in n),
    ("totalKjeldahlNitrogen", lambda n: "kjeld" in n),
    ("freeAmmonia", lambda n: "freeammonia" in n),
    ("ammoniacalNitrogen", lambda n: "ammoni" in n),
    ("totalHardness", lambda n: "hardn" in n),
    ("calciumHardness", lambda n: re.match(r"(ca|calcium)as(caco3|caco)", n) is not None),
    ("magnesiumHardness", lambda n: re.match(r"(mg|magnesium)as(caco3|caco)", n) is not None),
    # "Mg as Ca (mg/L)" in mid-2024 is a typo for magnesium as Mg.
    ("calcium", lambda n: re.match(r"(ca|calcium)(as(ca)?)?(mgl)?$", n) is not None),
    ("magnesium", lambda n: re.match(r"(mg|magnesium)(as(ca|mg)?)?(mgl)?$", n) is not None),
    ("sulphate", lambda n: "sulph" in n),
    ("sodiumPercent", lambda n: "sodiumperc" in n),
    ("sodium", lambda n: "sodium" in n),
    ("orthoPhosphate", lambda n: "ortho" in n),
    ("phosphate", lambda n: "phosph" in n),
    ("boron", lambda n: "boron" in n or n.startswith("oron")),
    ("potassium", lambda n: "potass" in n),
    ("fluoride", lambda n: "fluor" in n),
    ("sar", lambda n: n == "sar"),
    ("cadmium", lambda n: "cadmium" in n),
    ("copper", lambda n: "copper" in n),
    ("lead", lambda n: n.startswith("lead")),
    ("chromium", lambda n: "chromium" in n),
    ("nickel", lambda n: "nickel" in n),
    ("zinc", lambda n: "zinc" in n),
    ("iron", lambda n: n.startswith("iron")),
    ("manganese", lambda n: "manganese" in n),
    ("saprobityIndex", lambda n: "saprob" in n),
    ("diversityIndex", lambda n: "diversity" in n),
]

# Pieces of the report title that bleed into the header cells below it.
TITLE_BLEED = re.compile(
    r"water\s*qual\w*|uality|ity\s+data\s+of|data\s+of|\bben\w*galu\w*|\blakes\b|\bfor\s+the\b|month\s+of(\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)?|\b20\d\d\b|\s-\s",
    re.I,
)

VALUE = re.compile(r"^(?:BDL|NA|ND|-|_|#VALUE!|[<>]?\d*\.?\d+(?:E[+-]?\d+)?(?:\(BDL\))?|\d*\.?\(BDL\)|\d+\.BDL)$", re.I)


def squash(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def header_key(raw, previous_raw):
    text = TITLE_BLEED.sub(" ", raw or "")
    n = squash(text)
    # July 2023 prints "Potassium Fl" and leaves the last header empty: the "Fl" starts "Fluoride".
    if n == "" and re.sub(r"mgl$", "", squash(previous_raw)).endswith("fl"):
        return "fluoride"
    # Title text can cover the first header cell entirely; a first column of numbers is the code or serial.
    for key, test in HEADER_RULES:
        if test(n):
            return key
    raise ValueError(f"unknown column header {raw!r}")


def cell_text(chars):
    return (extract_text(chars, x_tolerance=2, y_tolerance=1) or "").strip()


def looks_like_value(text):
    last = text.split("\n")[-1].replace(" ", "")
    return bool(last) and bool(VALUE.match(last))


def title_of(pdf):
    text = pdf.pages[0].extract_text(y_tolerance=1) or ""
    match = re.search(r"Water\s+Quality\s+Data[^\n]*", text, re.I)
    return re.sub(r"\s+", " ", match.group(0)).strip() if match else ""


# ---------- ruled tables ----------


def grid(page):
    """
    The page's biggest table as drawn: rows x cells x chars, each whole token placed
    in the cell that holds its centre, plus the table's row boxes and column x ranges.
    """
    tables = page.find_tables()
    if not tables:
        return None
    table = max(tables, key=lambda t: len(t.rows))
    if len(table.rows) < 3:
        return None
    rows = [(r.bbox[1], r.bbox[3], list(r.cells)) for r in table.rows]
    width = max(len(r[2]) for r in rows)
    columns = [None] * width
    for _, _, cells in reversed(rows):
        for j, cell in enumerate(cells):
            if cell and columns[j] is None:
                columns[j] = (cell[0], cell[2])
    tops = [r[0] for r in rows]
    buckets = [[[] for _ in r[2]] for r in rows]
    for word in tokens(page):
        cx = (word[0]["x0"] + word[-1]["x1"]) / 2
        for ch in word:
            cy = (ch["top"] + ch["bottom"]) / 2
            i = bisect.bisect_right(tops, cy) - 1
            if i < 0 or cy > rows[i][1]:
                continue
            for j, cell in enumerate(rows[i][2]):
                if cell and cell[0] <= cx <= cell[2]:
                    buckets[i][j].append(ch)
                    break
    return buckets, rows, columns


def column_of(token, columns):
    cx = (token[0]["x0"] + token[-1]["x1"]) / 2
    for j, span in enumerate(columns):
        if span and span[0] <= cx <= span[1]:
            return j
    return None


def centre_y(token):
    return (token[0]["top"] + token[0]["bottom"]) / 2


# Columns of one row can sit up to ~0.6pt apart (different fonts); a wrapped line sits >= 1.1pt off.
SAME_LINE = 0.9


def is_value(token):
    return bool(VALUE.match("".join(c["text"] for c in token).strip("\"'")))


def place_blocks(page, columns, anchors, top):
    """
    Rows in these sheets are often shorter than their wrapped text, so a long name's second
    line is drawn inside the next row's box. Excel draws each cell's text in one go, though:
    a run of tokens drawn one after another in the same column is one cell. Each such block
    belongs to the first row whose value line is at or below the block's first line.
    """
    cells = [[[] for _ in columns] for _ in anchors]
    block, block_col = [], None

    def flush():
        text_tokens = [t for t in block if not t[0]["text"].isspace()]
        if not text_tokens or block_col is None:
            return
        first = min(centre_y(t) for t in text_tokens)
        i = bisect.bisect_left(anchors, first - SAME_LINE)
        if i == len(anchors):
            if first - anchors[-1] > 8:
                return
            i = len(anchors) - 1
        for t in block:
            cells[i][block_col].extend(t)

    last = None
    for token in tokens(page):
        y = centre_y(token)
        if y < top:
            continue
        if token[0]["text"].isspace():
            block.append(token)
            continue
        j = column_of(token, columns)
        # Text too long for its cell runs on into the next column on the same line; it stays in its cell.
        runs_on = (
            last is not None
            and abs(y - centre_y(last)) <= 0.3
            and 0 <= token[0]["x0"] - last[-1]["x1"] <= 3
            and not is_value(token)
            and not is_value(last)
        )
        new_line = last is not None and abs(y - centre_y(last)) > 0.6
        starts_row = new_line and any(abs(y - a) <= SAME_LINE for a in anchors)
        if (j != block_col and not runs_on) or starts_row or (new_line and y < centre_y(last)):
            flush()
            block, block_col = [], j
        block.append(token)
        last = token
    flush()
    return cells


def tokens(page):
    """
    Runs of chars as the PDF draws them. Values in crowded columns overlap their
    neighbours on the page ("0.00059(BDL)0.00067(BDL)"), but each value is still
    drawn as one run, so following the drawing order keeps them apart.
    """
    out, current = [], []
    for ch in page.chars:
        if current:
            prev = current[-1]
            joined = (
                abs(ch["top"] - prev["top"]) < 0.5
                and -0.5 <= ch["x0"] - prev["x1"] <= 1
                and not ch["text"].isspace()
                and not prev["text"].isspace()
            )
            if not joined:
                out.append(current)
                current = []
        current.append(ch)
    if current:
        out.append(current)
    return out


def lines_of(chars, gap=1.2):
    """Y centres of the text lines in a cell."""
    ys = sorted((c["top"] + c["bottom"]) / 2 for c in chars)
    lines = []
    for y in ys:
        if lines and y - lines[-1][-1] <= gap:
            lines[-1].append(y)
        else:
            lines.append([y])
    return [sum(line) / len(line) for line in lines]


def row_anchors(row, anchor_cols):
    """Y of each station's value line in a drawn row; several when borders between rows are missing."""
    best = max((lines_of(row[j]) for j in anchor_cols if j < len(row)), key=len, default=[])
    return best


def parse_ruled(pdf):
    keys, rows = None, []
    for page in pdf.pages:
        drawn = grid(page)
        if not drawn:
            continue
        buckets, boxes, columns = drawn
        header_rows, anchors, top = [], [], None
        for row, box in zip(buckets, boxes):
            texts = [cell_text(c) for c in row]
            if sum(looks_like_value(t) for t in texts) < max(3, len(texts) * 0.5):
                if keys is None and not rows:
                    header_rows.append(row)
                continue
            if keys is None:
                keys = header_keys(header_rows, len(row))
            if len(row) != len(keys):
                filled = [t for t in texts if t]
                raise ValueError(f"row has {len(row)} cells, header has {len(keys)}: {filled[:4]}")
            if top is None:
                top = box[0] - 3
            # The code, serial or month cell is one short line per station: the best row marker.
            marker = [j for j, k in enumerate(keys) if k in ("code", "serial", "sampled")][:1]
            value_cols = [j for j, k in enumerate(keys) if k in ("ph", "dissolvedOxygen", "conductivity")]
            anchors.extend(row_anchors(row, marker + value_cols))
        if not anchors:
            continue
        for part in place_blocks(page, columns, sorted(anchors), top):
            # Header text that overflows into the first data row is bold; data never is.
            cells = [cell_text([c for c in chars if "Bold" not in c["fontname"]]) for chars in part]
            rows.append(dict(zip(keys, cells)))
    return keys, rows


def header_keys(header_rows, width):
    # The title sits in larger type above the header in most months; drop it.
    chars = [c for row in header_rows for cell in row for c in cell]
    size = Counter(round(c["size"], 1) for c in chars).most_common(1)[0][0] if chars else 0
    raws = []
    for j in range(width):
        cell = [c for row in header_rows if j < len(row) for c in row[j] if round(c["size"], 1) <= size * 1.2]
        raws.append(re.sub(r"\s+", " ", cell_text(cell)))
    keys = []
    for j, raw in enumerate(raws):
        if j == 0 and squash(TITLE_BLEED.sub(" ", raw)) in ("", "stn", "tn"):
            keys.append("code" if "code" in raw.lower() else "serial")
            continue
        keys.append(header_key(raw, raws[j - 1] if j else ""))
    dupes = [k for k, n in Counter(keys).items() if n > 1]
    if dupes:
        raise ValueError(f"duplicate columns {dupes} in header {raws}")
    return keys


# ---------- the unruled August 2023 table ----------

# Left edge (points) of each measurement column, measured on the August 2023 PDF.
AUG_2023_COLUMNS = [
    ("dissolvedOxygen", 203), ("ph", 234), ("conductivity", 249), ("bod", 277), ("nitrate", 297),
    ("fecalColiform", 322), ("totalColiform", 355), ("carbonate", 390), ("bicarbonate", 413),
    ("turbidity", 437), ("phenolphthaleinAlkalinity", 458), ("totalAlkalinity", 488), ("chloride", 518),
    ("cod", 548), ("ammoniacalNitrogen", 569), ("totalHardness", 591), ("calciumHardness", 610),
    ("magnesiumHardness", 630), ("sulphate", 652), ("sodium", 675), ("tds", 703), ("phosphate", 731),
    ("boron", 754), ("potassium", 781), ("fluoride", 801),
]
AUG_2023_TEXT = [("code", 0), ("sampled", 33), ("name", 60), ("useClass", 150)]


def parse_unruled(pdf):
    edges = AUG_2023_TEXT + AUG_2023_COLUMNS
    lefts = [x for _, x in edges]
    rows = []
    for page in pdf.pages:
        words = page.extract_words(x_tolerance=1.5, y_tolerance=1)
        anchors = [w for w in words if w["x0"] < 33 and re.fullmatch(r"\d{4}", w["text"])]
        if not anchors:
            continue
        ys = [(a["top"] + a["bottom"]) / 2 for a in anchors]
        first_top = min(ys) - 12  # wrapped names and classes start up to ~9pt above their code; the header ends ~15pt above
        cells = [[[] for _ in edges] for _ in anchors]
        for w in words:
            cy = (w["top"] + w["bottom"]) / 2
            if cy < first_top:
                continue
            i = min(range(len(ys)), key=lambda k: abs(ys[k] - cy))
            j = bisect.bisect_right(lefts, (w["x0"] + w["x1"]) / 2) - 1
            # Long names run on past the class column into the first measurement column,
            # sometimes touching its value ("Taluka4.6").
            if j >= len(AUG_2023_TEXT) and re.search(r"[a-z]", w["text"].replace("BDL", "")):
                glued = re.fullmatch(r"(.*[A-Za-z,)])(\d*\.?\d+(?:\(BDL\))?)", w["text"])
                if glued:
                    cells[i][j].append({**w, "text": glued.group(2)})
                    w = {**w, "text": glued.group(1)}
                j = 2
            cells[i][j].append(w)
        for row in cells:
            texts = [" ".join(w["text"] for w in sorted(c, key=lambda w: (round(w["top"]), w["x0"]))) for c in row]
            rows.append(dict(zip([k for k, _ in edges], texts)))
    return [k for k, _ in edges], rows


def parse(path):
    with pdfplumber.open(path) as pdf:
        title = title_of(pdf)
        ruled = any(p.rects for p in pdf.pages)
        keys, rows = parse_ruled(pdf) if ruled else parse_unruled(pdf)
    return title, keys or [], rows
