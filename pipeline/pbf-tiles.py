#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cuts the OSM extracts out of the Geofabrik australia-latest.osm.pbf — same
JSON shape as Overpass ('elements': ways with tags, node ids and geometry), so
build.mjs cannot tell the difference. Zürich: the road grid covers the city,
Glattal, Limmattal and the lake shores (34 x 33 km), the rail file reaches
Winterthur, Baden, Zug and Rapperswil with the S-Bahn, out of the Geofabrik
Switzerland extract in one pass.

Way ids are OSM's own; node ids ride along because buildGraph() builds the
topology from el.nodes and SILENTLY skips ways without them.
"""
import json, os, re, sys
import osmium

ROOT = os.path.join(os.path.dirname(__file__), '..')
PBFS = [os.path.join(ROOT, 'data', 'switzerland-latest.osm.pbf')]

# must match pipeline/download.sh and build.mjs
S, N, W, E = 47.25, 47.55, 8.35, 8.80
RAIL_BOX = (47.10, 8.10, 47.75, 9.10)
# the pre-filter below must admit anything inside EITHER box
FS, FW, FN, FE = min(S, RAIL_BOX[0]), min(W, RAIL_BOX[1]), max(N, RAIL_BOX[2]), max(E, RAIL_BOX[3])

HW = re.compile(r'^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|busway|construction|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$')
RAIL = re.compile(r'^(subway|tram|light_rail|rail|narrow_gauge|construction)$')  # narrow_gauge: the Forchbahn

road_tiles = {}
for i in range(1, 26):
    f = os.path.join(ROOT, f'data/osm/tiles/t{i}.json')
    if os.path.exists(f):
        continue
    row, col = (i - 1) // 5, (i - 1) % 5
    road_tiles[i] = (S + (N - S) * row / 5, S + (N - S) * (row + 1) / 5,
                     W + (E - W) * col / 5, W + (E - W) * (col + 1) / 5)
rail_file = os.path.join(ROOT, 'data/osm/zurich-rail.json')
need_rail = not os.path.exists(rail_file)
print('brakujące kafle dróg:', sorted(road_tiles), '| szyny:', need_rail, flush=True)
if not road_tiles and not need_rail:
    sys.exit(0)
os.makedirs(os.path.join(ROOT, 'data/osm/tiles'), exist_ok=True)

out = {i: [] for i in road_tiles}
out_rail = []


class H(osmium.SimpleHandler):
    def way(self, w):
        tags = w.tags
        hw = tags.get('highway')
        rw = tags.get('railway')
        is_road = bool(road_tiles) and hw is not None and HW.match(hw)
        is_rail = need_rail and rw is not None and RAIL.match(rw)
        if not is_road and not is_rail:
            return
        geom, ids = [], []
        la0, la1, lo0, lo1 = 90.0, -90.0, 180.0, -180.0
        for n in w.nodes:
            try:
                lo, la = n.lon, n.lat
            except osmium.InvalidLocationError:
                continue
            ids.append(n.ref)
            geom.append({'lat': la, 'lon': lo})
            if la < la0: la0 = la
            if la > la1: la1 = la
            if lo < lo0: lo0 = lo
            if lo > lo1: lo1 = lo
        if len(geom) < 2:
            return
        # the whole country goes by: drop anything outside the frame first
        if la1 < FS or la0 > FN or lo1 < FW or lo0 > FE:
            return
        el = None

        def make():
            nonlocal el
            if el is None:
                el = {'type': 'way', 'id': w.id, 'nodes': ids,
                      'tags': {t.k: t.v for t in tags}, 'geometry': geom}
            return el

        if is_road:
            for i, (s, n_, w_, e) in road_tiles.items():
                if la1 >= s and la0 <= n_ and lo1 >= w_ and lo0 <= e:
                    out[i].append(make())
        if is_rail:
            s, w_, n_, e = RAIL_BOX
            if la1 >= s and la0 <= n_ and lo1 >= w_ and lo0 <= e:
                out_rail.append(make())


for pbf in PBFS:
    if not os.path.exists(pbf):
        sys.exit(f'brak {pbf} — pobierz go (pipeline/download.sh)')
    print('czytam', os.path.basename(pbf), flush=True)
    H().apply_file(pbf, locations=True, idx='flex_mem')

GEN = 'pbf-tiles.py (Geofabrik switzerland)'
for i, els in out.items():
    f = os.path.join(ROOT, f'data/osm/tiles/t{i}.json')
    json.dump({'version': 0.6, 'generator': GEN, 'elements': els}, open(f, 'w'))
    print(f't{i}: {len(els)} dróg', flush=True)
if need_rail:
    json.dump({'version': 0.6, 'generator': GEN, 'elements': out_rail}, open(rail_file, 'w'))
    print(f'szyny: {len(out_rail)} odcinków', flush=True)
print('gotowe', flush=True)
