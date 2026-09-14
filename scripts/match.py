"""
Spatial matching helpers. All distances are in metres, computed in UTM zone 43N,
which covers Bengaluru with negligible distortion.

Matching rule for the whole project: location first, name second.
A name is only ever used to pick between lakes that are already close,
or, when a source has no location at all, when the name is unique among all lakes.
"""

import re
from difflib import SequenceMatcher

from pyproj import Transformer
from shapely import STRtree
from shapely.geometry import Point, shape
from shapely.ops import transform

from common import name_key

_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True).transform


def to_utm(geom):
    return transform(_to_utm, geom)


def utm_point(lon, lat):
    return Point(_to_utm(float(lon), float(lat)))


def name_similarity(a, b):
    ka, kb = name_key(a), name_key(b)
    if not ka or not kb:
        return 0.0
    score = 1.0 if ka == kb else SequenceMatcher(None, ka, kb).ratio()
    # "Mallasandra Lake-1" and "Mallasandra Lake-2" are different lakes.
    na, nb = re.findall(r"\d+", a), re.findall(r"\d+", b)
    if na and nb and na != nb:
        score *= 0.5
    return score


class LakeIndex:
    """
    A spatial index over lakes. Each lake is (key, name, utm_geometry).
    Point lakes (disappeared, no outline) are indexed as circles of their recorded size.
    """

    def __init__(self, lakes):
        """lakes: (key, name or list of names, utm_geometry). The first name is the display name."""
        self.keys = [k for k, _, _ in lakes]
        self.aliases = [[n] if isinstance(n, str) or n is None else [x for x in n if x] for _, n, _ in lakes]
        self.names = [a[0] if a else "" for a in self.aliases]
        self.geoms = [g for _, _, g in lakes]
        self.tree = STRtree(self.geoms)
        self.by_key = {k: i for i, k in enumerate(self.keys)}
        self._unique_names = None

    def add_aliases(self, key, names):
        i = self.by_key[key]
        self.aliases[i] += [n for n in names if n and n not in self.aliases[i]]
        self._unique_names = None

    def name_score(self, i, name):
        """Best similarity between a name and any name the lake is known by."""
        return max((name_similarity(name, a) for a in self.aliases[i]), default=0.0)

    def geom(self, key):
        return self.geoms[self.by_key[key]]

    def near(self, geom, within_m):
        """Candidate (index, distance) pairs within a distance of a UTM geometry."""
        idx = self.tree.query(geom, predicate="dwithin", distance=within_m)
        return [(int(i), self.geoms[i].distance(geom)) for i in idx]

    def match_point(self, lon, lat, name=None, within_m=150, name_floor=0.0, name_weight=100):
        """
        Best lake for a point: inside or closest, with the name breaking ties among nearby lakes.
        Returns (key, distance_m, name_score) or None.
        """
        p = utm_point(lon, lat)
        best = None
        for i, d in self.near(p, within_m):
            score = self.name_score(i, name) if name else 0.0
            if name and score < name_floor and d > 0:
                continue
            # By default inside beats outside and a good name is worth ~100 m. Sources with
            # rough coordinates (monitoring stations) raise name_weight so the name decides.
            rank = d - name_weight * score
            if best is None or rank < best[0]:
                best = (rank, self.keys[i], round(d), round(score, 2))
        return None if best is None else best[1:]

    def match_polygon(self, geom_utm, min_share=0.3):
        """
        Lake with the largest overlap. The share is measured against the smaller shape,
        so a lake drawn slightly larger or smaller in another source still matches.
        Returns (key, share) or None.
        """
        best = None
        for i in self.tree.query(geom_utm, predicate="intersects"):
            other = self.geoms[i]
            inter = other.intersection(geom_utm).area
            smaller = min(other.area, geom_utm.area) or 1
            share = inter / smaller
            if share >= min_share and (best is None or share > best[1]):
                best = (self.keys[i], round(share, 2))
        return best

    def match_unique_name(self, name):
        """
        Only for sources with no usable location: accept a name if exactly one lake has it.
        An exact name ("Ulsoor Lake") is tried before the loose key, which would also
        match "Ulsoor Kunte".
        """
        if self._unique_names is None:
            exact, loose = {}, {}
            for key, names in zip(self.keys, self.aliases):
                for n in names:
                    exact.setdefault(exact_key(n), set()).add(key)
                    loose.setdefault(name_key(n), set()).add(key)
            self._unique_names = (
                {k: next(iter(v)) for k, v in exact.items() if k and len(v) == 1},
                {k: next(iter(v)) for k, v in loose.items() if k and len(v) == 1},
            )
        exact, loose = self._unique_names
        return exact.get(exact_key(name)) or loose.get(name_key(name))


def exact_key(name):
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def feature_utm(feature):
    return to_utm(shape(feature["geometry"]))
