"""
Everything the section builders need: the registry, the crosswalk, and every source
table indexed by its own ID, so a builder can ask "what does source X say about lake Y".
"""

import json
from collections import defaultdict

from shapely.geometry import shape

from common import ROOT, SOURCES, read_csv
from match import LakeIndex, feature_utm, utm_point


def _rows(file):
    path = SOURCES / file
    return read_csv(path) if path.exists() else []


def _features(file):
    path = SOURCES / file
    return json.loads(path.read_text())["features"] if path.exists() else []


class Section(dict):
    """
    One part of a lake record. Facts are plain values; `src` maps each fact to the
    source key a "See source" link resolves through sources.json ("per-entry" when each
    item in a list carries its own `source`). Empty values are left out so the record
    only holds what we actually know.
    """

    def set(self, field, value, source):
        if value is None or value == "" or value == [] or value == {}:
            return self
        self[field] = value
        if source:
            # A fact drawn from several documents at once cites all of them.
            keys = source.split(";") if ";" in source else source
            self.setdefault("src", {})[field] = keys
        return self

    def done(self):
        return dict(self) if any(k != "src" for k in self) else None


class Context:
    def __init__(self):
        self.registry = {r["id"]: r for r in read_csv(ROOT / "data" / "registry.csv")}
        self.lakes = {f["properties"]["id"]: f for f in json.loads((ROOT / "data" / "lakes.geojson").read_text())["features"]}
        self.by_fid = {r["atreeFid"]: r["id"] for r in self.registry.values() if r["atreeFid"]}
        self._index = None

        self.links = defaultdict(lambda: defaultdict(list))  # id -> source -> [link]
        for link in read_csv(ROOT / "data" / "crosswalk.csv"):
            self.links[link["id"]][link["source"]].append(link)

        self.atree = {str(f["properties"]["atreeFid"]): f["properties"] for f in _features("atree.geojson")}
        self.empri = {r["empriCode"]: r for r in _rows("empri2018.csv")}
        self.hist = {f["properties"]["histId"]: f["properties"] for f in _features("historic_water.geojson")}
        self.osm = {f["properties"]["osmId"]: f["properties"] for f in _features("osm_water.geojson")}
        self.wikidata = {r["qid"]: r for r in _rows("wikidata.csv")}
        self.wiki_summaries = defaultdict(dict)
        for r in _rows("wikipedia_summaries.csv"):
            self.wiki_summaries[r["qid"]][r["lang"]] = r
        self.bbmp_lms = {r["bbmpLmsId"]: r for r in _rows("bbmp_lms.csv")}
        self.wbc = {r["wbcId"]: r for r in _rows("wbc2018.csv")}
        self.mi_tanks = {r["miTankId"]: r for r in _rows("mi_tanks.csv")}
        self.kgis_tanks = {str(f["properties"]["kgisTankId"]): f["properties"] for f in _features("kgis_tanks.geojson")}
        self.custody = {f"{r['slNo']}-{r['parcelIndex']}": r for r in _rows("bbmp_custody.csv")}
        self.ktcda = {f"{r['slNo']}-{r['custodian']}": r for r in _rows("ktcda_custodians.csv")}
        self.lake_groups = {str(n): r for n, r in enumerate(_rows("lake_groups.csv"))}
        self.landrecords = {r["mapId"]: r for r in _rows("landrecords_lakes_digital.csv") + _rows("landrecords_lakes_survey.csv")}
        self.kspcb_stations = {r["stationId"]: r for r in _rows("kspcb_stations.csv")}
        self.kspcb_readings = defaultdict(list)
        for r in _rows("kspcb_readings.csv"):
            self.kspcb_readings[r["stationId"]].append(r)
        self.wq_historic = defaultdict(list)
        for r in _rows("wq_historic.csv"):
            self.wq_historic[f"{r['dataset']}:{r['stationId']}"].append(r)
        self.empri_wq = defaultdict(list)
        for r in _rows("empri2018_water_quality.csv"):
            self.empri_wq[r["empriCode"]].append(r)

        # Per-lake stats: keyed by our id, or by atreeFid until they are rerun on the full list.
        self.stats = {name: self._per_lake(f"{name}.csv") for name in ("jrc_water", "worldcover", "dem", "cascade", "gbif", "inaturalist", "historic_presence")}
        self.sentinel2 = defaultdict(dict)
        for r in _rows("sentinel2.csv"):
            lake_id = self._lake_key(r)
            if lake_id:
                self.sentinel2[lake_id][r["season"]] = r
        self.jrc_yearly = self._per_lake_many("jrc_yearly.csv")
        self.gbif_species = self._per_lake_many("gbif_species.csv")
        self.photos = self._per_lake_many("commons_photos.csv")

        # Plant locations come from OpenStreetMap: BWSSB's published points put several
        # plants (Hebbal, V. Valley) at the K&C Valley site. Unnamed plants are left out.
        self.treatment_plants = []
        for f in _features("osm_features.geojson"):
            p = f["properties"]
            if p["kind"] != "wastewater_plant" or not p.get("name") or "pump" in p["name"].lower():
                continue
            c = shape(f["geometry"]).representative_point()
            self.treatment_plants.append({"name": p["name"], "lat": c.y, "lon": c.x, "capacityMld": p.get("capacityMld"), "source": p["source"]})
        self.wards = _features("wards_2025_gba_369.geojson")

        self.sources = {}
        for path in sorted(SOURCES.glob("*.sources.json")):
            for entry in json.loads(path.read_text()):
                self.sources[entry["key"]] = entry

    def _lake_key(self, row):
        for col in ("id", "key", "atreeFid"):
            value = row.get(col)
            if value is None:
                continue
            if value in self.registry:
                return value
            if value in self.by_fid:
                return self.by_fid[value]
        return None

    def _per_lake(self, file):
        out = {}
        for r in _rows(file):
            lake_id = self._lake_key(r)
            if lake_id:
                out[lake_id] = r
        return out

    def _per_lake_many(self, file):
        out = defaultdict(list)
        for r in _rows(file):
            lake_id = self._lake_key(r)
            if lake_id:
                out[lake_id].append(r)
        return out

    def find_by_name(self, name, point, within_m, exclude=None, floor=0.8):
        """The lake near a point whose name best matches, if any matches well."""
        if self._index is None:
            self._index = LakeIndex([(k, f["properties"].get("names") or [f["properties"]["name"]], feature_utm(f)) for k, f in self.lakes.items()])
        best = None
        for i, _ in self._index.near(utm_point(*point), within_m):
            key = self._index.keys[i]
            score = self._index.name_score(i, name)
            if key != exclude and score >= floor and (best is None or score > best[1]):
                best = (key, score)
        return best[0] if best else None

    def linked(self, lake_id, source):
        return self.links[lake_id].get(source, [])

    def first(self, lake_id, source, table):
        """The first linked record from a source, looked up in its table."""
        for link in self.linked(lake_id, source):
            row = table.get(link["sourceId"])
            if row:
                return row
        return None
