# Zürich Public Transport — interactive map

Interactive, poster-grade map of public transport in **Zürich and its
agglomeration**: the ZVV buses and VBZ trolleybuses, all the trams and the
S-Bahn of the 25 km ring — drawn along the real street and track geometry.

## Live

**https://miqell24.github.io/zurich-bus-map/** — GitHub Pages serves
`main:/docs`; local build on port 8184 (`npm run serve`).

Two feeds. The ZVV publishes its trams and buses as one GTFS on the city's
open data portal (<https://data.stadt-zuerich.ch/dataset/vbz_fahrplandaten_gtfs>,
CC0, one zip per timetable year) — the whole Verbund, Winterthur and the
Zürcher Oberland included, with shapes; the S-Bahn is not in it. The S-Bahn
comes from the **Swiss national GTFS** (<https://opentransportdata.swiss/>,
read from the MobilityDatabase mirror), which ships no shapes at all, so its
lines are matched from their station sequences on the rail graph.
`pipeline/scope.mjs` cuts both to Zürich (`data/scope.json`):

| mode | feed | route_type | scope | graph |
|---|---|---|---|---|
| buses | ZVV | 3 | ≥50% of stops within 15 km of the HB, no stop past 30 km | OSM roadways |
| trolleybuses | ZVV | 3 | VBZ's 31, 32, 33, 34, 46, 72, 83 — green | OSM roadways |
| trams | ZVV | 0 | all VBZ routes 2–17, family red | `railway=tram` |
| S-Bahn | national (+ ZVV for the Forchbahn S18) | 109 (2) | ≥50% of stops within 25 km, no stop past 55 km — 35 lines in ZVV's blue | `railway=rail` + `light_rail` |

Fifteen kilometres is the city, Glattal, Limmattal and the lake shores;
Winterthur (22 km, its own buses 1–14) and Uster stay out of the frame — and
so their numbers never collide with Zürich's trams. Cut deliberately: the
funiculars (route_type 7 — Polybahn, Dolderbahn, Rigiblick), the "E" extra
trams, everything of the national feed that is not an S-line.

Line keys need nothing invented: trams 2–17, city buses 29–99, regional
buses 1xx–9xx, night buses N1–N95, the S-Bahn S2–S42 and SN1–SN9. Night
lines (N-buses, SN-trains) print at the end of their lists, the trolleybuses
at the head of the bus list. The stop names drop the "Zürich, " town prefix
the feed puts on every pole in the city.

## Pipeline

`npm run download` fetches both feeds (the newest yearly ZVV zip through the
CKAN API), computes the scope and cuts the OSM extract. **The OSM data comes
from Geofabrik, not Overpass**: `switzerland-latest.osm.pbf` comes down once
and `pipeline/pbf-tiles.py` (needs `pip3 install --user osmium`) cuts a 5 × 5
road grid over the agglomeration (34 × 33 km) and the rail file out to the
ends of the S-Bahn, writing exactly the JSON shape Overpass would have
returned, node ids included.

`npm run build` map-matches every line (HMM/Viterbi on the OSM graphs) and
writes GeoJSON to `data/out/`; `npm run lines` adds the line-by-line view;
`npm run audit` checks the drawn result. `npm run serve` hosts the map at
<http://localhost:8184>.

Data: ZVV (GTFS, CC0) · opentransportdata.swiss · base map © OpenFreeMap /
OpenMapTiles / OpenStreetMap contributors.
