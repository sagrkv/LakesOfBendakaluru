"""
The ATREE-CSEI stream network inside BBMP, as a directed graph. Used by cascade.py. Not a source itself.

The KML gives FROM_NODE/TO_NODE per segment, but the digitised direction is no guide to flow:
about half the segments run against the DEM. So each segment is oriented by the DEM instead:
water runs towards the end with the larger upstream area in a DEM routing with the streams burned in.
"""

import re
from collections import defaultdict

import numpy as np
import requests
import shapely
from shapely.geometry import LineString

URL = (
    "https://data.opencity.in/dataset/14aaf1e9-d3a9-4d5a-b698-bb93bd064264/resource/"
    "733f491b-3e74-49fd-b6fc-dde2fc0fda0e/download/23141cb5-471e-4796-af80-4311819fd031.kml"
)
MAX_STEPS = 200_000


def fetch(path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(URL, timeout=300)
        response.raise_for_status()
        path.write_bytes(response.content)
    return path


def parse(path):
    """Segments as (arcid, [(lon, lat), ...]) in digitised order."""
    text = path.read_text(encoding="utf-8")
    segments = []
    for placemark in re.findall(r"<Placemark>(.*?)</Placemark>", text, re.S):
        coords = re.search(r"<coordinates>([^<]*)</coordinates>", placemark)
        arcid = re.search(r'<SimpleData name="ARCID">(\d+)<', placemark)
        if not coords or not arcid:
            continue
        points = [tuple(round(float(v), 7) for v in chunk.split(",")[:2]) for chunk in coords.group(1).split()]
        if len(points) >= 2:
            segments.append((int(arcid.group(1)), points))
    return segments


class StreamGraph:
    """
    Vertices of all segments, joined where segments share an end point, with one directed edge
    between consecutive vertices of a segment.

    The published lines are broken by one-pixel gaps (about 30 m) at many junctions, so a loose
    end within SNAP_DEG of another segment is joined to that segment's nearest vertex.
    """

    SNAP_DEG = 0.0004  # about 45 m, one and a half pixels of the 1 arc-second grid the streams were traced on

    def __init__(self, segments, upstream_area):
        """upstream_area(lon, lat) -> DEM upstream area near that point, used to orient the flow."""
        self.index = {}
        self.xy = []
        self.out = defaultdict(list)
        self.kml_downhill = 0
        owners = defaultdict(set)
        ends = defaultdict(int)
        for n, (_, points) in enumerate(segments):
            if upstream_area(*points[-1]) < upstream_area(*points[0]):
                points = points[::-1]
            else:
                self.kml_downhill += 1
            ids = [self._vertex(p) for p in points]
            for v in ids:
                owners[v].add(n)
            ends[ids[0]] += 1
            ends[ids[-1]] += 1
            for a, b in zip(ids, ids[1:]):
                if a != b:
                    self.out[a].append(b)
        self.xy = np.array(self.xy)
        self.segment_count = len(segments)
        self.area = np.array([upstream_area(x, y) for x, y in self.xy])
        self.snapped = self._snap([v for v, count in ends.items() if count == 1], owners)

    def _snap(self, loose, owners):
        tree = shapely.STRtree(shapely.points(self.xy))
        joined = 0
        for v in loose:
            near = tree.query(shapely.Point(self.xy[v]).buffer(self.SNAP_DEG))
            near = [u for u in near if not owners[u] & owners[v]]
            if not near:
                continue
            u = min(near, key=lambda u: np.hypot(*(self.xy[u] - self.xy[v])))
            if np.hypot(*(self.xy[u] - self.xy[v])) > self.SNAP_DEG:
                continue
            a, b = (v, u) if self.area[v] <= self.area[u] else (u, v)
            if b not in self.out[a]:
                self.out[a].append(b)
                joined += 1
        return joined

    def _vertex(self, point):
        key = (round(point[0], 6), round(point[1], 6))
        if key not in self.index:
            self.index[key] = len(self.xy)
            self.xy.append(point)
        return self.index[key]

    def edges(self):
        return [(a, b) for a, targets in self.out.items() for b in targets]

    def outlet(self, lake_buffered, edge_tree, edge_list):
        """
        The edge by which the stream leaves a lake: among edges touching the (slightly buffered)
        outline whose downstream end lies outside it, the one carrying the most water.
        Returns (upstream vertex, downstream vertex), or None when no stream touches the lake.
        """
        best = None
        for i in edge_tree.query(lake_buffered, predicate="intersects"):
            a, b = edge_list[i]
            if shapely.contains_xy(lake_buffered, *self.xy[b]):
                continue
            if best is None or self.area[b] > self.area[best[1]]:
                best = (a, b)
        return best

    def trace(self, edge, own_key, lake_tree, lake_keys, lake_geoms):
        """
        Follow the flow from an outlet edge to the first lake other than own_key.
        At a split, takes the branch carrying more water. Returns the lake key or None.
        """
        seen = set()
        a, b = edge
        for _ in range(MAX_STEPS):
            line = LineString([self.xy[a], self.xy[b]])
            hits = [i for i in lake_tree.query(line, predicate="intersects") if lake_keys[i] != own_key]
            if hits:
                start = shapely.Point(self.xy[a])
                return lake_keys[min(hits, key=lambda i: lake_geoms[i].distance(start))]
            targets = self.out.get(b)
            if not targets or b in seen:
                return None
            seen.add(b)
            a, b = b, max(targets, key=lambda t: self.area[t])
        return None
