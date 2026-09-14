"""
Water segmentation for the historic map sheets, one method per drawing style.

  soi-colour   Survey of India coloured sheets (1916-1929). Water that "generally contains
               water" is filled blue. On one-inch and half-inch sheets the rest of a tank's
               bed is a dense dot screen inside a black outline; both count as the tank.
               Marshy beds (blue dashes on white) are not taken: dashed blue lines through
               white cantonment land look the same to a colour rule.
  soi-stipple  Survey of India 1945 black-and-white reprint: tanks are an irregular dot
               stipple with no fill colour and often no outline.
  ams          US Army Map Service 1955: perennial water solid blue, intermittent tanks
               blue hatching; blue grid lines cross the whole sheet.

Each returns a boolean mask in scan pixels: True = water body, and a second mask marking
which of those pixels were blue (as opposed to dot screen only), used for confidence.
"""

import cv2
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree


def disc(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def blue_mask(img, p):
    """
    Blue print. Either an HSV box (clean scans with saturated blue), or for faded scans
    the blue-minus-red tint after a blur, which averages the pale halftone tank fill
    and separates it from cream paper and warm grey hill shading.
    """
    if "tintMin" in p:
        b = cv2.GaussianBlur(img, (0, 0), p["tintBlur"]).astype(np.int16)
        tint = b[..., 0] - b[..., 2]
        # Black print is neutral too, so a tint rule on its own takes every letter and line.
        light = b.max(axis=2) >= p.get("tintValMin", 0)
        threshold = p["tintMin"]
        if isinstance(threshold, list):
            threshold = tint_gap(tint[::4, ::4][light[::4, ::4]], *threshold)
        return (tint >= threshold) & light

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    hue = p["blueHue"]
    blue = (h >= hue[0]) & (h <= hue[1]) & (s >= p["blueSatMin"])
    light = blue & (v >= p["blueValMin"])
    if "darkBlueHaloPx" in p:
        # Dark blue ink (hill form lines, a rubber stamp) has a lighter halo that passes
        # as water; drop light blue right next to it.
        dark = (blue & (v < p["blueValMin"] - 20)).astype(np.uint8)
        dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, disc(1))
        light &= ~cv2.dilate(dark, disc(p["darkBlueHaloPx"])).astype(bool)
    return light


def tint_gap(values, lo, hi):
    """
    The blue-minus-red value between a sheet's land and its water: the middle of the longest
    run of near-empty 2-unit histogram bins in [lo, hi). Water covers a few percent of a
    sheet, land the rest, and the paper's tint shifts from sheet to sheet.
    """
    counts, edges = np.histogram(values, bins=np.arange(lo, hi + 1, 2))
    sparse = counts <= counts.min() + 0.0002 * len(values)
    best, start = (0, lo), None
    for i, s in enumerate(list(sparse) + [False]):
        if s and start is None:
            start = i
        elif not s and start is not None:
            if i - start > best[0]:
                best = (i - start, (edges[start] + edges[i]) / 2)
            start = None
    return best[1]


def dot_density(img, dark_max, dot_area, window, bright_min, grey_max=255, neighbours=None, paper_px=5, green_max=None):
    """
    Count of small isolated dark dots per window: the dot screens used for tank beds.
    Letters, lines and symbols are larger connected shapes and are not counted.
    Only neutral grey dots (channel spread <= grey_max) on pale paper count, so the
    bluish halftone of hill shading and dotted boundaries through coloured land do not.
    neighbours = (radius, count): keep only dots with at least `count` other dots within
    `radius` px. Dots in a fill have neighbours on all sides; dots in a dotted line have two.
    """
    ink = img.max(axis=2)
    spread = ink.astype(np.int16) - img.min(axis=2)
    dark = (ink < dark_max) & (spread <= grey_max)
    if green_max is not None:
        # Dark green plantation dots pass as grey after JPEG compression; black print has no green cast.
        b, g, r = (img[..., i].astype(np.int16) for i in range(3))
        dark &= g - np.maximum(b, r) <= green_max
    dark = dark.astype(np.uint8)
    _, _, stats, cent = cv2.connectedComponentsWithStats(dark, connectivity=8)
    area = stats[:, cv2.CC_STAT_AREA]
    w, h = stats[:, cv2.CC_STAT_WIDTH], stats[:, cv2.CC_STAT_HEIGHT]
    is_dot = (area >= dot_area[0]) & (area <= dot_area[1]) & (w <= dot_area[2]) & (h <= dot_area[2])
    is_dot[0] = False
    dots = np.zeros(dark.shape, np.float32)
    cx, cy = cent[is_dot, 0].astype(int), cent[is_dot, 1].astype(int)
    if neighbours and len(cx):
        radius, count = neighbours[:2]
        pts = np.column_stack([cx, cy])
        tree = cKDTree(pts)
        groups = tree.query_ball_point(pts, radius)
        keep = np.array([len(v) - 1 >= count for v in groups])
        if len(neighbours) > 2:
            # Optional third value: the neighbours must spread in two directions. A dotted line
            # (field boundaries print dots 6 px apart) has several neighbours, all along one line;
            # a screen has them all round. Kept when the spread across is at least this share of the spread along.
            min_ratio = neighbours[2]
            for i in np.flatnonzero(keep):
                offsets = pts[groups[i]] - pts[i]
                spread = np.sqrt(np.clip(np.linalg.eigvalsh(np.cov(offsets.T)), 0, None))
                keep[i] = spread[1] > 0 and spread[0] >= min_ratio * spread[1]
        cx, cy = cx[keep], cy[keep]
    dots[cy, cx] = 1.0
    # Paper around the dots: darkest-channel median over a window wider than one dot
    # (coarse screens print dots that fill a 5 px window on their own).
    paper = cv2.medianBlur(img.min(axis=2), paper_px) >= bright_min
    dots *= paper
    return cv2.boxFilter(dots, -1, (window, window), normalize=False)


def fill_holes(mask, max_hole_px):
    """Fill holes up to a size: names printed inside a tank, gaps in the dot screen."""
    filled = ndimage.binary_fill_holes(mask)
    holes = filled & ~mask
    n, labels, stats, _ = cv2.connectedComponentsWithStats(holes.astype(np.uint8), connectivity=4)
    small = np.zeros(n, bool)
    small[1:] = stats[1:, cv2.CC_STAT_AREA] <= max_hole_px
    return mask | small[labels]


def soi_colour(img, p):
    blue = cv2.morphologyEx(blue_mask(img, p).astype(np.uint8), cv2.MORPH_CLOSE, disc(1))
    # Remove streams and well symbols: keep only blue that survives an opening.
    blue = cv2.morphologyEx(blue, cv2.MORPH_OPEN, disc(p["openPx"])).astype(bool)
    water = blue.copy()
    if p.get("dotScreen"):
        density = dot_density(
            img,
            p["dotDarkMax"],
            p["dotArea"],
            p["dotWindow"],
            p["dotPaperMin"],
            p.get("dotGreyMax", 255),
            p.get("dotNeighbours"),
            p.get("dotPaperPx", 5),
            p.get("dotGreenMax"),
        )
        bed = density >= p["dotMinCount"]
        # Beds are broad fills; a wider opening than for blue drops the small clusters of
        # dotted symbols (scrub, tree screens) that a coarse dot screen lets through.
        bed = cv2.morphologyEx(bed.astype(np.uint8), cv2.MORPH_OPEN, disc(p.get("dotOpenPx", p["openPx"]))).astype(bool)
        water |= bed
    water = cv2.morphologyEx(water.astype(np.uint8), cv2.MORPH_CLOSE, disc(p["closePx"])).astype(bool)
    return fill_holes(water, p["maxHolePx"]), blue


def soi_stipple(img, p):
    density = dot_density(
        img,
        p["dotDarkMax"],
        p["dotArea"],
        p["dotWindow"],
        p["dotPaperMin"],
        p.get("dotGreyMax", 255),
        p.get("dotNeighbours"),
        p.get("dotPaperPx", 5),
    )
    bed = density >= p["dotMinCount"]
    bed = cv2.morphologyEx(bed.astype(np.uint8), cv2.MORPH_OPEN, disc(p.get("dotOpenPx", p["openPx"])))
    bed = cv2.morphologyEx(bed, cv2.MORPH_CLOSE, disc(p["closePx"])).astype(bool)
    return fill_holes(bed, p["maxHolePx"]), np.zeros_like(bed)


def ams(img, p):
    blue = blue_mask(img, p).astype(np.float32)
    # Share of blue in a small window: solid and hatched tank fills are mostly blue,
    # stream lines and grid lines are not, even where several streams meet.
    w = p["densityWindow"]
    solid = (cv2.blur(blue, (w, w)) >= p["densityMin"]).astype(np.uint8)
    solid = cv2.morphologyEx(solid, cv2.MORPH_OPEN, disc(p["openPx"]))
    solid = cv2.morphologyEx(solid, cv2.MORPH_CLOSE, disc(p["closePx"])).astype(bool)
    return fill_holes(solid, p["maxHolePx"]), solid


STYLES = {"soi-colour": soi_colour, "soi-stipple": soi_stipple, "ams": ams}


def water_mask(img, sheet):
    return STYLES[sheet["style"]](img, sheet["water"])


def blank_mask(img, sheet):
    """
    Areas where the sheet draws no water at all, so absence there says nothing: the
    1955 sheets fill towns (all of central Bangalore) with flat yellow. None if the
    sheet has no such areas.
    """
    p = sheet["water"].get("blankYellow")
    if not p:
        return None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    yellow = ((h >= p["hue"][0]) & (h <= p["hue"][1]) & (s >= p["satMin"]) & (v >= p["valMin"])).astype(np.uint8)
    # Close over the roads and names printed across the town fill.
    yellow = cv2.morphologyEx(yellow, cv2.MORPH_CLOSE, disc(p["closePx"]))
    yellow = cv2.morphologyEx(yellow, cv2.MORPH_OPEN, disc(p["openPx"]))
    return ndimage.binary_fill_holes(yellow)
