"""
Page images, OCR and table columns for the scan of the 1986 Lakshman Rau report (see rau1986.py).

  - each page is rendered at its scan resolution (200 dpi), turned upright with tesseract's orientation
    check, and straightened by the angle that makes its text rows sharpest
  - tesseract gives word boxes, cached per page in data/cache/rau1986/
  - the conurbation tables print a column-number row ("1 2 ... 8") against a header rule that often strikes
    through the faint digits, so the digits are found as ink blobs and fitted to the table's usual layout
  - the lines that open a row carry every column, so they place the first four column edges

Tesseract (brew install tesseract) must be on the PATH.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CACHE  # noqa: E402

WORK = CACHE / "rau1986"


# ---------------------------------------------------------------- page images


def page_image(pdf, number):
    """The page as an upright, straightened black-and-white image."""
    path = WORK / f"page-{number:02d}.png"
    if path.exists():
        return cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    WORK.mkdir(parents=True, exist_ok=True)
    img = np.array(pdf.pages[number - 1].to_image(resolution=200).original.convert("L"))
    img = cv2.threshold(img, 160, 255, cv2.THRESH_BINARY)[1]
    img = deskew(rotate_upright(img))
    cv2.imwrite(str(path), img)
    return img


def tesseract(img, *args):
    ok, png = cv2.imencode(".png", img)
    return subprocess.run(["tesseract", "stdin", "stdout", *args], input=png.tobytes(), capture_output=True).stdout.decode()


def rotate_upright(img):
    m = re.search(r"Rotate: (\d+)", tesseract(img, "--psm", "0"))
    turns = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    angle = int(m.group(1)) if m else 0
    return cv2.rotate(img, turns[angle]) if angle in turns else img


def deskew(img):
    """Rotate by the small angle (within 3 degrees) at which the ink's row profile is sharpest."""
    ink = cv2.resize(255 - img, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA).astype(np.float32)
    h, w = ink.shape
    best = (0.0, 0.0)
    for angle in np.arange(-3, 3.01, 0.1):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1)
        sharpness = float(np.square(np.diff(cv2.warpAffine(ink, m, (w, h)).sum(axis=1))).sum())
        if sharpness > best[1]:
            best = (angle, sharpness)
    if abs(best[0]) < 0.05:
        return img
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), best[0], 1)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=255)


# ---------------------------------------------------------------- OCR


def ocr_words(img, number):
    """Word boxes: text, conf, x0, x1, top, bottom and the tesseract line they sit on."""
    path = WORK / f"page-{number:02d}.json"
    if path.exists():
        return json.loads(path.read_text())
    words = []
    for line in tesseract(img, "--psm", "6", "-c", "preserve_interword_spaces=1", "tsv").splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 12 or f[0] != "5" or not f[11].strip():
            continue
        left, top, width, height = map(int, f[6:10])
        words.append({
            "text": f[11].strip(), "conf": float(f[10]), "x0": left, "x1": left + width, "top": top, "bottom": top + height,
            "line": f"{f[2]}-{f[3]}-{f[4]}",
        })
    path.write_text(json.dumps(words))
    return words


def box_of(words):
    return (min(w["x0"] for w in words), max(w["x1"] for w in words), min(w["top"] for w in words), max(w["bottom"] for w in words))


def crop(img, box):
    """The part of the page inside (x0, x1, top, bottom)."""
    x0, x1, top, bottom = (int(round(v)) for v in box)
    return img[max(top, 0):max(bottom, 0), max(x0, 0):max(x1, 0)]


def read_band(band, scale, interpolation, whitelist):
    """One line of text in a cell crop, enlarged, with a restricted character set."""
    if band.size == 0 or not (band < 128).any():
        return ""
    big = cv2.resize(band, None, fx=scale, fy=scale, interpolation=interpolation)
    big = cv2.copyMakeBorder(big, 20, 20, 30, 30, cv2.BORDER_CONSTANT, value=255)
    return tesseract(big, "--psm", "7", "-c", f"tessedit_char_whitelist={whitelist}").strip()


def read_decimal(band):
    """
    A decimal number in a cell crop, with the point found as ink. The typed point is often too faint for
    tesseract but is a clear dot on the baseline: the digits are read with it erased, and the point goes back
    after as many digit shapes as stand left of it. Returns the number as text, or None when unsure.
    """
    ink_cols = np.where((band < 128).any(axis=0))[0] if band.size else []
    if len(ink_cols) == 0:
        return None
    # The number is the rightmost cluster of ink; a long name can reach into the crop from the left.
    start = ink_cols[-1]
    for a, b in zip(ink_cols[::-1][1:], ink_cols[::-1][:-1]):
        if b - a >= 30:
            break
        start = a
    band = band[:, max(start - 4, 0):ink_cols[-1] + 5]
    _, labels, stats, _ = cv2.connectedComponentsWithStats((band < 128).astype(np.uint8), 8)
    parts = [(i, x, y, w, h, a) for i, (x, y, w, h, a) in enumerate(stats) if i > 0]
    tall = [p for p in parts if p[4] >= 12]
    if not tall:
        return None
    height = max(p[4] for p in tall)
    digits = sorted((p for p in parts if p[4] >= 0.55 * height), key=lambda p: p[1])
    groups = []
    for p in digits:  # a digit the scan broke into pieces
        if groups and p[1] <= groups[-1][1] + 2:
            groups[-1][1] = max(groups[-1][1], p[1] + p[3])
        else:
            groups.append([p[1], p[1] + p[3]])
    base = float(np.median([p[2] + p[4] for p in digits]))
    dots = [
        p for p in parts
        if p[4] <= 0.4 * height and p[3] <= 0.5 * height and p[5] >= 4 and p[2] + p[4] >= base - 0.3 * height
        and groups[0][0] < p[1] + p[3] / 2 < groups[-1][1]
    ]
    if len(dots) != 1:
        return None
    digit_ids = {p[0] for p in digits}
    clean = band.copy()
    for p in parts:
        if p[0] not in digit_ids:
            clean[labels == p[0]] = 255
    text = re.sub(r"\D", "", read_band(clean, 2, cv2.INTER_NEAREST, "0123456789"))
    k = sum(1 for g in groups if (g[0] + g[1]) / 2 < dots[0][1] + dots[0][3] / 2)
    return f"{text[:k]}.{text[k:]}" if len(text) == len(groups) and 0 < k < len(text) else None


def lines_of(words):
    """Words grouped by tesseract line, top to bottom, each line left to right."""
    groups = {}
    for w in words:
        groups.setdefault(w["line"], []).append(w)
    return sorted((sorted(ws, key=lambda w: w["x0"]) for ws in groups.values()), key=top_of)


def legible_lines(words):
    """Lines with at least one word that is not a speck."""
    return [ws for ws in lines_of(words) if any(w["conf"] >= 20 or len(w["text"]) > 2 for w in ws)]


def line_text(ws):
    return " ".join(w["text"] for w in ws)


def top_of(ws):
    return min(w["top"] for w in ws)


# ---------------------------------------------------------------- columns


def header_rules(img):
    """y of each long horizontal rule in the top half of the page."""
    h, w = img.shape
    ink = (img[: h // 2] < 128).astype(np.uint8)
    lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (w // 12, 1)))
    rules = []
    for y in np.where(lines.sum(axis=1) > w * 0.15)[0]:
        if rules and y - rules[-1][-1] <= 4:
            rules[-1].append(int(y))
        else:
            rules.append([int(y)])
    return [(r[0] + r[-1]) // 2 for r in rules]


def number_blobs(img, top, bottom):
    """x centres of the single characters in a strip, with the rule through them erased."""
    ink = (img[max(top, 0):bottom] < 128).astype(np.uint8)
    rule = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (45, 1)))
    _, _, stats, _ = cv2.connectedComponentsWithStats(ink & (1 - rule), 8)
    merged = []
    for a, b in sorted((x, x + w) for x, y, w, h, _ in stats[1:] if 6 <= h <= 40 and w <= 40):
        if merged and a - merged[-1][1] <= 12:  # a digit the scan broke into pieces
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    return [(a + b) / 2 for a, b in merged]


def number_strips(img, n):
    """Candidate column-number rows in the strips just below and above each header rule: (strip bottom, blob xs)."""
    out = []
    for y in header_rules(img):
        for top, bottom in ((y + 3, y + 48), (y - 48, y - 3)):
            xs = number_blobs(img, top, bottom)
            if n - 1 <= len(xs) <= n + 1 and xs[-1] - xs[0] > img.shape[1] * 0.5:
                out.append((bottom, xs))
    return out


def fit_columns(xs, template):
    """
    Place found blobs on the table's usual column layout (positions scaled 0..1), allowing one faint
    digit to be missing or one speck extra. Typists shifted columns from page to page, so the layout
    only decides which blob is which; found blobs keep their own position and only a missing digit
    takes the fitted one. Returns (max error in px, the n centres) or None.
    """
    n = len(template)
    if len(xs) == n:
        options = [list(xs)]
    elif len(xs) == n + 1:
        options = [xs[:k] + xs[k + 1:] for k in range(n + 1)]
    elif len(xs) == n - 1:
        options = [xs[:k] + [None] + xs[k:] for k in range(n)]
    else:
        return None
    best = None
    for option in options:
        pairs = [(t, x) for t, x in zip(template, option) if x is not None]
        a, b = np.polyfit([t for t, _ in pairs], [x for _, x in pairs], 1)
        error = max(abs(a * t + b - x) for t, x in pairs)
        if best is None or error < best[0]:
            best = (error, [a * t + b if x is None else x for t, x in zip(template, option)])
    return best


def column_layout(pages_strips, n):
    """The usual column positions of a table, from its pages whose number row shows exactly n blobs."""
    exact = [xs for strips in pages_strips for _, xs in strips if len(xs) == n]
    if not exact:
        raise RuntimeError("rau1986: no page shows a clean column-number row")
    return [float(np.median([(xs[k] - xs[0]) / (xs[-1] - xs[0]) for xs in exact])) for k in range(n)]


def column_row(strips, template, max_error=150):
    """The strip that fits the table's layout best. Returns (bottom of the strip, n column centres)."""
    fits = []
    for bottom, xs in strips:
        fit = fit_columns(xs, template)
        if fit and fit[0] <= max_error:
            fits.append((fit[0], bottom, fit[1]))
    if not fits:
        return None, None
    _, bottom, centres = min(fits, key=lambda f: f[0])
    return bottom, centres


def boundaries(lines, centres, width):
    """Between each pair of column centres, the middle of the widest strip with the least ink from words."""
    cover = np.zeros(width + 1, dtype=np.int32)
    for ws in lines:
        for w in ws:
            cover[max(w["x0"], 0):min(w["x1"], width)] += 1
    edges = []
    for a, b in zip(centres, centres[1:]):
        lo, hi = int(a), int(b)
        if hi <= lo:
            edges.append((a + b) / 2)
            continue
        seg = cover[lo:hi]
        runs, start = [], None
        for x, v in enumerate(seg):
            if v == seg.min() and start is None:
                start = x
            if v != seg.min() and start is not None:
                runs.append((start, x))
                start = None
        if start is not None:
            runs.append((start, len(seg)))
        s, e = max(runs, key=lambda r: r[1] - r[0])
        edges.append(lo + (s + e) / 2)
    return edges


def refine_edges(lines, guesses, width, window=150):
    """Edges borrowed from another page, each moved to the widest least-inked strip within a window of its guess."""
    cover = np.zeros(width + 1, dtype=np.int32)
    for ws in lines:
        for w in ws:
            cover[max(w["x0"], 0):min(w["x1"], width)] += 1
    edges = []
    for g in guesses:
        lo, hi = max(int(g - window), 0), min(int(g + window), width)
        if hi <= lo:
            edges.append(g)
            continue
        seg = cover[lo:hi]
        runs, start = [], None
        for x, v in enumerate(seg):
            if v == seg.min() and start is None:
                start = x
            if v != seg.min() and start is not None:
                runs.append((start, x))
                start = None
        if start is not None:
            runs.append((start, len(seg)))
        s, e = max(runs, key=lambda r: r[1] - r[0])
        edges.append(lo + (s + e) / 2)
    return edges


SERIAL = re.compile(r"\W{0,2}\d{1,2}[.,]\W{0,2}")


def serial_x(lines, img):
    """Median right edge of the row serials ("12.") printed at the left of a page."""
    xs = [ws[0]["x1"] for ws in lines if ws[0]["x0"] < img.shape[1] * 0.25 and SERIAL.fullmatch(ws[0]["text"])]
    return float(np.median(xs)) if xs else 0.0


def row_edges(body, img):
    """
    The first four column edges from the lines that open a row ("12. 329 Kowdenahalli 18.06 The tank ..."):
    serial | tank number | name | area | location and condition. Returns four edges or None.
    """
    found = []
    for ws in body:
        if ws[0]["x0"] > img.shape[1] * 0.25 or not SERIAL.fullmatch(ws[0]["text"]):
            continue
        rest = ws[1:]
        area = next((i for i, w in enumerate(rest) if i >= 1 and re.fullmatch(r"\d{1,3}[.,]\d{1,2}", w["text"])), None)
        if area is None or area < 2 or area + 1 >= len(rest):
            continue
        tank = rest[0] if re.search(r"\d{2,3}", rest[0]["text"]) else None
        name = rest[1] if tank else rest[0]
        found.append((ws[0]["x1"], tank["x0"] if tank else None, name["x0"], rest[area]["x0"], rest[area]["x1"], rest[area + 1]["x0"]))
    if not found:
        return None

    def med(k):
        return float(np.median([f[k] for f in found if f[k] is not None]))

    tank_x0 = med(1) if any(f[1] is not None for f in found) else med(2) - 60
    return [(med(0) + tank_x0) / 2, med(2) - 8, med(3) - 8, (med(4) + med(5)) / 2]


def column_of(w, edges):
    """1-based column of a word by its left edge."""
    return 1 + sum(w["x0"] >= e for e in edges)
