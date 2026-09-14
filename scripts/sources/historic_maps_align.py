"""
Alignment of a georeferenced sheet against today's lakes.

A sheet's graticule gives lon/lat on the old Indian datum, drawn by hand a century ago.
Tanks rarely move, so today's lake outlines are good control: for every large lake we
find the shift that best overlays the historic water on it, then fit one smooth
correction (a translation, or an affine map when enough lakes spread over the sheet)
to all those shifts. Accuracy is reported as the leave-one-out residual: for each lake,
the error of a correction fitted without that lake.

All work is in UTM zone 43N metres.
"""

import numpy as np
from pyproj import Transformer
from rasterio import features
from rasterio.transform import from_origin
from scipy.signal import fftconvolve
from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import transform as shp_transform

TO_UTM = Transformer.from_crs(4326, 32643, always_xy=True)
TO_WGS = Transformer.from_crs(32643, 4326, always_xy=True)


def to_utm(geom):
    return shp_transform(TO_UTM.transform, geom)


def to_wgs(geom):
    return shp_transform(TO_WGS.transform, geom)


def rasterize(geoms, bounds, res):
    minx, miny, maxx, maxy = bounds
    w, h = int(np.ceil((maxx - minx) / res)), int(np.ceil((maxy - miny) / res))
    tf = from_origin(minx, maxy, res, res)
    if not geoms:
        return np.zeros((h, w), np.float32)
    return features.rasterize(((g, 1) for g in geoms), out_shape=(h, w), transform=tf, dtype="uint8").astype(np.float32)


def best_shift(hist, lake, max_px):
    """
    Shift (dx, dy) in pixels, east and north positive, that moves the historic mask onto
    the lake mask with the largest overlap, and that overlap in pixels.
    """
    corr = fftconvolve(lake, hist[::-1, ::-1], mode="full")
    cy, cx = hist.shape[0] - 1, hist.shape[1] - 1
    win = corr[cy - max_px : cy + max_px + 1, cx - max_px : cx + max_px + 1]
    iy, ix = np.unravel_index(np.argmax(win), win.shape)
    # Rows grow southwards, so a positive row shift is a move to the south.
    return ix - max_px, -(iy - max_px), float(win[iy, ix])


def fit_model(points, offsets, kind):
    """Least squares correction: offset = t (+ B (p - centre) for affine)."""
    if kind == "translation":
        return {"kind": kind, "t": np.median(offsets, axis=0)}
    centre = points.mean(axis=0)
    a = np.column_stack([np.ones(len(points)), (points - centre) / 1000.0])
    coef = np.linalg.lstsq(a, offsets, rcond=None)[0]
    return {"kind": kind, "centre": centre, "coef": coef}


def predict(model, points):
    points = np.atleast_2d(points)
    if model["kind"] == "translation":
        return np.repeat(model["t"][None], len(points), axis=0)
    a = np.column_stack([np.ones(len(points)), (points - model["centre"]) / 1000.0])
    return a @ model["coef"]


def robust_fit(points, offsets, kind):
    keep = np.ones(len(points), bool)
    for _ in range(5):
        model = fit_model(points[keep], offsets[keep], kind)
        err = np.hypot(*(offsets - predict(model, points)).T)
        limit = max(3 * 1.4826 * np.median(np.abs(err[keep] - np.median(err[keep]))) + np.median(err[keep]), 30)
        new_keep = err <= limit
        if (new_keep == keep).all():
            break
        keep = new_keep
    return fit_model(points[keep], offsets[keep], kind), keep


def leave_one_out(points, offsets, keep, kind):
    """Error at each lake of a correction fitted without that lake."""
    errs = np.full(len(points), np.nan)
    idx = np.flatnonzero(keep)
    for i in range(len(points)):
        others = idx[idx != i]
        if len(others) < 3:
            continue
        model = fit_model(points[others], offsets[others], kind)
        errs[i] = float(np.hypot(*(offsets[i] - predict(model, points[i])[0])))
    return errs


def align(hist_polys, footprint, lakes, cfg, named):
    """
    hist_polys: historic water polygons in UTM metres (uncorrected).
    footprint:  sheet neatline in UTM metres.
    lakes:      list of (id, name, polygon in UTM metres) for today's lakes.
    Returns (correct(geom) -> geom, report).
    """
    res = cfg["alignResM"]
    inside = [(i, n, g) for i, n, g in lakes if footprint.buffer(-200).contains(g.representative_point())]
    bounds = footprint.buffer(2500).bounds

    # 1. One shift for the whole sheet: mostly the datum difference.
    hist_r = rasterize(hist_polys, bounds, res)
    lake_r = rasterize([g for _, _, g in inside], bounds, res)
    max_px = int(cfg["maxShiftM"] / res)
    gx, gy, _ = best_shift(hist_r, lake_r, max_px)
    g_shift = np.array([gx * res, gy * res])
    shifted = [translate(p, *g_shift) for p in hist_polys]

    # 2. Local shift at every large lake, on top of the sheet shift. Each lake is matched
    # to the one historic polygon it overlaps most; only pairs of similar size are
    # control, since a small lake inside a big old tank has no defined offset.
    local_px = int(cfg["localShiftM"] / res)
    margin = cfg["localShiftM"] + 4 * res
    points, offsets, ids, control = [], [], [], []
    named_ids = set(named)
    for lake_id, name, g in inside:
        if g.area < cfg["minControlLakeM2"] and lake_id not in named_ids:
            continue
        reach = g.buffer(cfg["localShiftM"])
        near = [p for p in shifted if p.intersects(reach)]
        if not near:
            continue
        match = max(near, key=lambda p: (p.intersection(g).area, -p.distance(g)))
        ratio = match.area / g.area
        win = box(*g.union(match).bounds).buffer(margin, join_style=2)
        h = rasterize([match], win.bounds, res)
        lk = rasterize([g], win.bounds, res)
        dx, dy, overlap = best_shift(h, lk, local_px)
        if overlap < cfg["minControlOverlap"] * min(lk.sum(), h.sum()):
            continue
        c = g.centroid
        points.append((c.x, c.y))
        offsets.append((dx * res, dy * res))
        ids.append((lake_id, name))
        control.append(g.area >= cfg["minControlLakeM2"] and 0.5 <= ratio <= 2.0)
    points, offsets = np.array(points, float).reshape(-1, 2), np.array(offsets, float).reshape(-1, 2)
    control = np.array(control, bool)
    all_points, all_offsets = points, offsets
    points, offsets = points[control], offsets[control]

    # 3. Correction model.
    # Affine only with enough lakes, and only if it predicts left-out lakes better.
    kinds = ["translation", "affine"] if len(points) >= cfg.get("minAffineLakes", 12) else ["translation"]
    if len(points) >= 3:
        best = None
        for kind in kinds:
            model, keep = robust_fit(points, offsets, kind)
            loo = leave_one_out(points, offsets, keep, kind)
            score = np.nanmedian(loo)
            if best is None or score < best[0]:
                best = (score, model, keep, loo)
        _, model, keep, loo = best
    else:
        model, keep, loo = {"kind": "translation", "t": np.zeros(2)}, np.ones(len(points), bool), np.array([])

    def correct(geom):
        def f(x, y, z=None):
            p = np.column_stack([np.asarray(x) + g_shift[0], np.asarray(y) + g_shift[1]])
            d = predict(model, p)
            return tuple(p[:, 0] + d[:, 0]), tuple(p[:, 1] + d[:, 1])

        return shp_transform(f, geom)

    raw = np.hypot(*(offsets + g_shift).T) if len(points) else np.array([])
    ok = ~np.isnan(loo) if len(loo) else np.array([], bool)
    control_idx = np.flatnonzero(control)
    named_rows = []
    for lake_id, label in named.items():
        hit = [k for k, (i, _) in enumerate(ids) if i == lake_id]
        if not hit:
            if any(i == lake_id for i, _, _ in inside):
                named_rows.append({"lake": label, "atreeFid": lake_id, "note": "not matched on this sheet"})
            continue
        k = hit[0]
        before = float(np.hypot(*(all_offsets[k] + g_shift)))
        c = np.flatnonzero(control_idx == k)
        if len(c) and not np.isnan(loo[c[0]]):
            after, used = float(loo[c[0]]), bool(keep[c[0]])
        else:
            # Not control (size changed too much): error of the full correction at this lake.
            after, used = float(np.hypot(*(all_offsets[k] - predict(model, all_points[k])[0]))), False
        named_rows.append(
            {
                "lake": label,
                "atreeFid": lake_id,
                "offsetBeforeM": round(before),
                "residualAfterM": round(after),
                "usedAsControl": used,
            }
        )
    report = {
        "sheetShiftM": {"east": round(float(g_shift[0])), "north": round(float(g_shift[1]))},
        "controlLakes": len(points),
        "controlLakesKept": int(keep.sum()),
        "correction": model["kind"],
        "offsetBeforeMedianM": round(float(np.median(raw))) if len(raw) else None,
        "residualMedianM": round(float(np.median(loo[ok]))) if ok.any() else None,
        "residualP90M": round(float(np.percentile(loo[ok], 90))) if ok.any() else None,
        "namedLakes": named_rows,
        "controlDetail": [
            {
                "id": ids[k],
                "offsetM": [round(float(v)) for v in all_offsets[k] + g_shift],
                "residualM": None if np.isnan(loo[j]) else round(float(loo[j])),
                "kept": bool(keep[j]),
            }
            for j, k in enumerate(control_idx)
        ],
    }
    return correct, report
