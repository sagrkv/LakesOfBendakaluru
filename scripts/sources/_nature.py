"""
Shared helpers for the nature sources (gbif, inaturalist). Not a source itself.

  - lake_shapes(): reads the input lake file and returns one search shape per lake,
    the outline (or a circle for a point) grown by a buffer, in WGS84.
  - Http: a polite GET client with a descriptive User-Agent, a request-rate cap,
    and retries with backoff. Safe to share across threads.
"""

import argparse
import json
import math
import threading
import time
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parent.parent.parent
USER_AGENT = "LakesOfBendakaluru/1.0 (open data project)"
ACRE_M2 = 4046.8564224
POINT_RADIUS_M = 100

# UTM 43N covers Bengaluru; buffers are computed in metres there.
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True).transform
TO_WGS = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True).transform


def lake_args(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("geometry", nargs="?", default="data/sources/atree.geojson", help="lake GeoJSON file")
    parser.add_argument("key", nargs="?", default="atreeFid", help="property that identifies each lake")
    return parser.parse_args()


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def lake_shapes(path, key, buffer_m):
    """
    Yield (key value, WGS84 shape) for every lake in the file.
    Polygons keep their outer rings only (islands count as lake), grown by buffer_m.
    Points become a circle of the recorded extent (recordedAcres) or 100 m, plus buffer_m.
    """
    features = json.loads((ROOT / path).read_text(encoding="utf-8"))["features"]
    for feature in features:
        props = feature.get("properties") or {}
        if feature.get("geometry") is None or props.get(key) is None:
            continue
        geom = transform(TO_UTM, shape(feature["geometry"]))
        if geom.geom_type in ("Point", "MultiPoint"):
            acres = number(props.get("recordedAcres"))
            radius = math.sqrt(acres * ACRE_M2 / math.pi) if acres else POINT_RADIUS_M
            grown = geom.buffer(radius + buffer_m)
        else:
            parts = getattr(geom, "geoms", [geom])
            grown = unary_union([Polygon(p.exterior) for p in parts if p.geom_type == "Polygon"]).buffer(buffer_m)
        yield props[key], transform(TO_WGS, grown)


class Http:
    def __init__(self, min_interval, retries=6):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.min_interval = min_interval
        self.retries = retries
        self.lock = threading.Lock()
        self.next_slot = 0.0

    def wait_turn(self):
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next_slot)
            self.next_slot = slot + self.min_interval
        time.sleep(max(0.0, slot - now))

    def get(self, url, params=None):
        """GET JSON. Returns None on 404 or an empty body, raises after the last retry."""
        for attempt in range(self.retries):
            self.wait_turn()
            try:
                response = self.session.get(url, params=params, timeout=90)
                if response.status_code == 404:
                    return None
                if response.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"{response.status_code} from {url}", response=response)
                response.raise_for_status()
                # Some GBIF endpoints answer 200 with an empty body when there is nothing to report.
                return response.json() if response.content.strip() else None
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError, ValueError) as error:
                status = getattr(getattr(error, "response", None), "status_code", None)
                if status is not None and status not in (429, 500, 502, 503, 504):
                    raise
                if attempt == self.retries - 1:
                    raise
                time.sleep(min(120, 2 ** attempt * (5 if status == 429 else 2)))
        return None


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(path)
