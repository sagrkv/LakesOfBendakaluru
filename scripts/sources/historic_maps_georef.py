"""
Georeferencing for the historic map sheets.

Each sheet covers a known block of latitude and longitude. Its neatline, and on most
Survey of India sheets a set of interior graticule lines, are printed at known values.
We trace each of those lines along its whole length in the scan, fit a smooth curve to
it, and take the crossings of meridians and parallels as control points. A polynomial
from pixels to the sheet's own map projection is fitted to the crossings.

Lon/lat come out on the sheet's datum (Everest spheroid, Indian datum). The shift to
WGS 84 is measured afterwards against today's lakes (historic_maps_align.py).
"""

import cv2
import numpy as np
from pyproj import CRS, Transformer

EVEREST = "+ellps=evrst30"


def sheet_crs(sheet):
    """The projection the sheet was drawn in, close enough for fitting."""
    west, south, east, north = sheet["bounds"]
    if sheet["projection"] == "tm":
        return CRS.from_proj4(f"+proj=tmerc +lon_0={(west + east) / 2} {EVEREST} +units=m +no_defs")
    # Survey of India sheets are polyconic, one projection per sheet.
    return CRS.from_proj4(
        f"+proj=poly +lat_0={(south + north) / 2} +lon_0={(west + east) / 2} {EVEREST} +units=m +no_defs"
    )


def poly_terms(x, y, order):
    x, y = np.asarray(x, float), np.asarray(y, float)
    terms = [np.ones_like(x), x, y]
    if order >= 2:
        terms += [x * x, x * y, y * y]
    if order >= 3:
        terms += [x**3, x * x * y, x * y * y, y**3]
    return np.stack(terms, axis=-1)


class SheetTransform:
    """
    Pixel <-> sheet lon/lat. `order` 1-3 fits a polynomial in the sheet's projection;
    "projective" fits a homography, used when only the four corners are known.
    """

    def __init__(self, sheet, pixels, lonlats, order):
        self.crs = sheet_crs(sheet)
        self.to_proj = Transformer.from_crs(self.crs.geodetic_crs, self.crs, always_xy=True)
        self.to_geo = Transformer.from_crs(self.crs, self.crs.geodetic_crs, always_xy=True)
        self.order = order
        px = np.asarray(pixels, float)
        en = np.stack(self.to_proj.transform(*np.asarray(lonlats, float).T), axis=1)
        self.px_c, self.px_s = px.mean(0), px.std() or 1.0
        self.en_c, self.en_s = en.mean(0), en.std() or 1.0
        p, q = (px - self.px_c) / self.px_s, (en - self.en_c) / self.en_s
        if order == "projective":
            self.h_fwd, _ = cv2.findHomography(p, q)
            self.h_inv = np.linalg.inv(self.h_fwd)
        else:
            a, b = poly_terms(*p.T, order), poly_terms(*q.T, order)
            self.c_fwd = np.linalg.lstsq(a, q, rcond=None)[0]
            self.c_inv = np.linalg.lstsq(b, p, rcond=None)[0]
        self.residuals_m = np.hypot(*(self.pixel_to_proj(*px.T) - en.T))
        centre = self.px_c
        e0 = self.pixel_to_proj([centre[0]], [centre[1]])
        e1 = self.pixel_to_proj([centre[0] + 100], [centre[1]])
        self.metres_per_px = float(np.hypot(*(e1 - e0))[0] / 100)

    def _apply(self, u, v, forward):
        pts = np.stack([np.asarray(u, float), np.asarray(v, float)], axis=1)
        if self.order == "projective":
            h = self.h_fwd if forward else self.h_inv
            return cv2.perspectiveTransform(pts[None], h)[0]
        return poly_terms(*pts.T, self.order) @ (self.c_fwd if forward else self.c_inv)

    def pixel_to_proj(self, x, y):
        p = (np.stack([np.asarray(x, float), np.asarray(y, float)], 1) - self.px_c) / self.px_s
        return (self._apply(*p.T, True) * self.en_s + self.en_c).T

    def pixel_to_lonlat(self, x, y):
        return self.to_geo.transform(*self.pixel_to_proj(x, y))

    def lonlat_to_pixel(self, lon, lat):
        e, n = self.to_proj.transform(np.asarray(lon, float), np.asarray(lat, float))
        q = (np.stack([e, n], 1) - self.en_c) / self.en_s
        return (self._apply(*q.T, False) * self.px_s + self.px_c).T


def line_offset(ink, x, y, vertical, half, along, contrast, min_share):
    """
    Where a straight line crosses a short strip centred on (x, y): for a vertical line the
    column, for a horizontal one the row. `ink` is the brightest channel of the scan, so
    only black print is dark (not blue water or purple grids). Returns the position of
    the line closest to the prediction, or None if no column/row is dark along most of
    the strip.
    """
    h, w = ink.shape
    if vertical:
        x0, x1, y0, y1 = int(x) - half, int(x) + half + 1, int(y) - along, int(y) + along + 1
    else:
        x0, x1, y0, y1 = int(x) - along, int(x) + along + 1, int(y) - half, int(y) + half + 1
    if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
        return None
    win = ink[y0:y1, x0:x1]
    # Black relative to the local paper tint, which varies across old scans.
    dark = win < np.percentile(win, 75) - contrast
    score = dark.mean(axis=0 if vertical else 1)
    peaks = [
        i
        for i in range(1, len(score) - 1)
        if score[i] >= min_share and score[i] >= score[i - 1] and score[i] >= score[i + 1]
    ]
    if not peaks:
        return None
    i = min(peaks, key=lambda p: abs(p - half))
    lo, hi = i, i
    while lo > 0 and score[lo - 1] >= score[i] * 0.8:
        lo -= 1
    while hi < len(score) - 1 and score[hi + 1] >= score[i] * 0.8:
        hi += 1
    return (int(x) if vertical else int(y)) - half + (lo + hi) / 2


def trace_line(ink, fit, sheet, fixed, value, extent, contrast):
    """
    Follow one meridian (fixed="lon") or parallel (fixed="lat") across the sheet and fit
    a quadratic to it: x = f(y) for meridians, y = f(x) for parallels.
    Returns (coefficients, share of samples found) or (None, share).
    """
    half, along = sheet.get("searchPx", 12), sheet.get("stripPx", 12)
    lo, hi = extent
    samples = np.linspace(lo + (hi - lo) * 0.02, hi - (hi - lo) * 0.02, 80)
    found = []
    for s in samples:
        lon, lat = (value, s) if fixed == "lon" else (s, value)
        px, py = fit.lonlat_to_pixel([lon], [lat])
        px, py = float(px[0]), float(py[0])
        pos = line_offset(ink, px, py, fixed == "lon", half, along, contrast, sheet.get("minLineShare", 0.7))
        if pos is not None:
            found.append((py, pos) if fixed == "lon" else (px, pos))
    share = len(found) / len(samples)
    if share < sheet.get("minLineFound", 0.4):
        return None, share
    t, u = np.array(found).T
    keep = np.ones(len(t), bool)
    for _ in range(4):
        coef = np.polyfit(t[keep], u[keep], 2)
        resid = np.abs(np.polyval(coef, t) - u)
        keep = resid < max(1.5, 3 * np.median(resid[keep]))
    if keep.mean() < 0.6:
        return None, share
    return np.polyfit(t[keep], u[keep], 2), share


def cross(meridian, parallel, guess):
    """Crossing of x = m(y) and y = p(x), by fixed-point iteration from a guess."""
    x, y = guess
    for _ in range(20):
        x = np.polyval(meridian, y)
        y = np.polyval(parallel, x)
    return float(x), float(y)


def georeference(sheet, img):
    """
    Trace the graticule and fit the transform.
    Returns (transform, report).
    """
    ink = img.max(axis=2)
    contrast = sheet.get("lineContrast", 45)
    west, south, east, north = sheet["bounds"]
    corner_ll = [(west, north), (east, north), (east, south), (west, south)]
    # Rough corners, picked by eye once, give the first prediction of where lines run.
    fit = SheetTransform(sheet, sheet["cornersPx"], corner_ll, "projective")
    if not sheet.get("traceLines", True):
        # Neatline too broken to trace (overprinted grid, labels): the corners, picked by
        # eye at 4x zoom, are the control points.
        return fit, {
            "controlPoints": 4,
            "linesNotTraced": [],
            "transform": "projective (4 corners, by eye)",
            "rmsResidualM": None,
            "maxResidualM": None,
            "metresPerPx": round(fit.metres_per_px, 2),
        }

    step = sheet["graticuleDeg"]
    if step and sheet.get("interiorLines", True):
        lons = list(np.round(np.arange(west, east + step / 2, step), 6))
        lats = list(np.round(np.arange(south, north + step / 2, step), 6))
    else:
        lons, lats = [west, east], [south, north]

    # Two passes: the second follows the lines predicted by the first, better fit.
    for _ in range(2):
        meridians = {v: trace_line(ink, fit, sheet, "lon", v, (south, north), contrast) for v in lons}
        parallels = {v: trace_line(ink, fit, sheet, "lat", v, (west, east), contrast) for v in lats}
        missing = [f"lon {v}" for v, (c, _) in meridians.items() if c is None]
        missing += [f"lat {v}" for v, (c, _) in parallels.items() if c is None]
        for edge in (west, east):
            if meridians[edge][0] is None:
                raise RuntimeError(f"{sheet['key']}: neatline at lon {edge} not traced")
        for edge in (south, north):
            if parallels[edge][0] is None:
                raise RuntimeError(f"{sheet['key']}: neatline at lat {edge} not traced")
        points, lonlats = [], []
        for lon, (m, _) in meridians.items():
            for lat, (p, _) in parallels.items():
                if m is None or p is None:
                    continue
                gx, gy = fit.lonlat_to_pixel([lon], [lat])
                points.append(cross(m, p, (gx[0], gy[0])))
                lonlats.append((lon, lat))
        order = sheet.get("order") or (2 if len(points) >= 9 else "projective")
        fit = SheetTransform(sheet, points, lonlats, order)

    report = {
        "controlPoints": len(points),
        "linesNotTraced": missing,
        "transform": f"polynomial order {order}" if order != "projective" else "projective (4 corners)",
        # Four corners fit a projective transform exactly, so there is no residual to report.
        "rmsResidualM": None if order == "projective" else round(float(np.sqrt((fit.residuals_m**2).mean())), 1),
        "maxResidualM": None if order == "projective" else round(float(fit.residuals_m.max()), 1),
        "metresPerPx": round(fit.metres_per_px, 2),
    }
    return fit, report
