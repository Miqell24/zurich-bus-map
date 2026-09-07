#!/usr/bin/env bash
# Downloads input data: the ZVV GTFS, the Swiss national GTFS, the OSM extract (Geofabrik), MapLibre GL.
# Everything is cached — re-running only fetches what is missing.
#
# Zürich: two feeds. The ZVV tram-and-bus timetable is on the city's open
# data portal (data.stadt-zuerich.ch, "VBZ Fahrplandaten GTFS", CC0, one zip
# per timetable year — the newest is read from the CKAN API); the S-Bahn is
# only in the Swiss national GTFS (opentransportdata.swiss), read from the
# MobilityDatabase mirror (mdb-2898, no token needed). Both are cut to
# Zürich by pipeline/scope.mjs → data/scope.json.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/osm/tiles web/vendor

need_osmium () {
  python3 -c "import osmium" 2>/dev/null && return 0
  echo "brak pakietu osmium — zainstaluj: pip3 install --user osmium" >&2
  return 1
}

# 1) ZVV — the newest yearly zip of the dataset
if [ ! -f data/gtfs-vbz/routes.txt ]; then
  echo "== ZVV Fahrplandaten GTFS =="
  URL=$(curl -s "https://data.stadt-zuerich.ch/api/3/action/package_show?id=vbz_fahrplandaten_gtfs" \
    | python3 -c "import json,sys; r=sorted([x['url'] for x in json.load(sys.stdin)['result']['resources'] if x['url'].endswith('_google_transit.zip')]); print(r[-1])" 2>/dev/null \
    || echo "https://data.stadt-zuerich.ch/dataset/vbz_fahrplandaten_gtfs/download/2026_google_transit.zip")
  curl -fL --retry 3 --max-time 900 -A "Mozilla/5.0" -o data/vbz.zip "$URL"
  mkdir -p data/gtfs-vbz
  unzip -q -o data/vbz.zip -d data/gtfs-vbz
fi

# 1b) the national feed (S-Bahn) — 160 MB, no shapes
if [ ! -f data/gtfs-ch/routes.txt ]; then
  echo "== Swiss national GTFS (MobilityDatabase mirror of opentransportdata.swiss) =="
  curl -fL --retry 3 --max-time 1800 -o data/ch.zip "https://files.mobilitydatabase.org/mdb-2898/latest.zip"
  mkdir -p data/gtfs-ch
  unzip -q -o data/ch.zip -d data/gtfs-ch
fi

# 1c) scope
if [ ! -f data/scope.json ]; then
  node --max-old-space-size=8192 pipeline/scope.mjs
fi

# 2) OSM — from the Geofabrik extract; pipeline/pbf-tiles.py cuts the 5 × 5
#    road grid (the city and its agglomeration) and the rail file (to the ends
#    of the S-Bahn) in the JSON shape Overpass would have returned.
if [ ! -f data/osm/tiles/t25.json ] || [ ! -f data/osm/zurich-rail.json ]; then
  need_osmium
  if [ ! -f data/switzerland-latest.osm.pbf ]; then
    echo "== Geofabrik switzerland-latest.osm.pbf =="
    curl -fL --retry 5 --retry-delay 5 -C - --max-time 3600 -o data/switzerland-latest.osm.pbf \
      "https://download.geofabrik.de/europe/switzerland-latest.osm.pbf"
  fi
  echo "== cutting OSM tiles out of the extract =="
  python3 pipeline/pbf-tiles.py
fi

# 3) MapLibre GL (vendored, no CDN at runtime)
if [ ! -f web/vendor/maplibre-gl.js ]; then
  echo "== MapLibre GL =="
  curl -fL --retry 3 -o web/vendor/maplibre-gl.js  https://unpkg.com/maplibre-gl@5.6.1/dist/maplibre-gl.js
  curl -fL --retry 3 -o web/vendor/maplibre-gl.css https://unpkg.com/maplibre-gl@5.6.1/dist/maplibre-gl.css
fi

echo "OK — data ready:"
du -sh data/gtfs-* data/osm 2>/dev/null || true
