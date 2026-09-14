"""
The home page draws every existing lake in its true geographic position and nothing else:
no roads, no boundaries, no basemap. Equirectangular is accurate enough across half a
degree of the city, so longitude is scaled by cos(latitude) and Y is flipped.
"""

import math

WIDTH = 1000.0
TOLERANCE = 0.00015  # degrees, roughly 15 metres: plenty for a ~1000px drawing


def simplify(ring, tolerance):
    """Douglas-Peucker on one ring."""
    if len(ring) < 4:
        return ring

    def perpendicular(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == 0 and dy == 0:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
        return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))

    keep = [False] * len(ring)
    keep[0] = keep[-1] = True
    stack = [(0, len(ring) - 1)]
    while stack:
        start, end = stack.pop()
        worst, index = tolerance, None
        for i in range(start + 1, end):
            d = perpendicular(ring[i], ring[start], ring[end])
            if d > worst:
                worst, index = d, i
        if index is not None:
            keep[index] = True
            stack.append((start, index))
            stack.append((index, end))
    return [p for p, k in zip(ring, keep) if k]


def outer_rings(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    if geometry["type"] == "MultiPolygon":
        return [poly[0] for poly in geometry["coordinates"]]
    return []


class Frame:
    """The drawing frame around a set of lon/lat points, WIDTH units wide, Y down."""

    def __init__(self, points):
        self.min_x, max_x = min(p[0] for p in points), max(p[0] for p in points)
        min_y, self.max_y = min(p[1] for p in points), max(p[1] for p in points)
        self.k = math.cos(math.radians((min_y + self.max_y) / 2))
        self.scale = WIDTH / ((max_x - self.min_x) * self.k)
        self.width = WIDTH
        self.height = round((self.max_y - min_y) * self.scale, 1)

    def project(self, p):
        return round((p[0] - self.min_x) * self.k * self.scale, 1), round((self.max_y - p[1]) * self.scale, 1)


def frame_points(geometry):
    """Every lon/lat vertex that should sit inside the frame."""
    if geometry["type"] == "Point":
        return [geometry["coordinates"]]
    return [p for ring in outer_rings(geometry) for p in ring]


def build_hero(lakes, frame):
    """lakes: (id, name, acres, geometry) for every lake to draw; frame: the shared Frame."""
    project = frame.project
    shapes = []
    for lake_id, name, acres, geometry in lakes:
        parts = []
        for ring in outer_rings(geometry):
            simple = simplify(ring, TOLERANCE)
            parts.append("M" + "L".join(f"{x} {y}" for x, y in map(project, simple if len(simple) >= 4 else ring)) + "Z")
        if parts:
            shapes.append({"id": lake_id, "name": name, "acres": acres, "d": "".join(parts)})
    return {"width": frame.width, "height": frame.height, "shapes": shapes}
