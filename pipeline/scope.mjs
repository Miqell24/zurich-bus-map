// Wyznacza zakres mapy Zurychu i zapisuje listy route_id do data/scope.json.
// Dwa feedy:
//  1) ZVV „Fahrplan Tram und Bus" (data.stadt-zuerich.ch, CC0) — tramwaje i
//     autobusy CAŁEGO Zürcher Verkehrsverbund, od Winterthuru po Zurzach.
//     Reguła: linia należy do mapy, gdy >=50% jej przystanków leży w
//     promieniu 15 km od Zürich HB (47.378, 8.540) i żaden nie dalej niż
//     30 km — miasto, Glattal, Limmattal, Zimmerberg; Winterthur (22 km,
//     własne autobusy 1–14) i Uster zostają poza kadrem, więc numery się
//     nie gryzą.
//  2) krajowy GTFS Szwajcarii (opentransportdata.swiss przez lustro
//     MobilityDatabase mdb-2898; BEZ shapes) — stamtąd tylko S-Bahn: trasy
//     route_type 109 o nazwie S…/SN…, >=50% przystanków w promieniu 25 km
//     i limit 55 km (S-Bahn Zürich sięga Winterthuru, Baden, Zugu,
//     Rapperswilu i Schaffhausen).
//
// Uruchamiane przez download.sh po pobraniu GTFS; build.mjs wymaga wyniku.
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { iterCsv, readCsv } from './lib/csv.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const CX = 8.540, CY = 47.378;          // Zürich HB
const mx = 111320 * Math.cos(CY * Math.PI / 180), my = 111132;
const t0 = Date.now();
const log = (m) => console.log(`[scope ${((Date.now() - t0) / 1000).toFixed(0)}s] ${m}`);

async function select(dir, keep, coreKm, share, capKm, label) {
  const GD = join(ROOT, dir);
  const cand = new Map();
  for (const r of await readCsv(join(GD, 'routes.txt'))) if (keep(r)) cand.set(r.route_id, (r.route_short_name || '').trim());
  log(`${label}: kandydatów ${cand.size}`);
  const stopKm = new Map();
  for await (const s of iterCsv(join(GD, 'stops.txt'))) {
    const lat = Number(s.stop_lat), lon = Number(s.stop_lon);
    if (Number.isFinite(lat) && Number.isFinite(lon)) stopKm.set(s.stop_id, Math.hypot((lon - CX) * mx, (lat - CY) * my) / 1000);
  }
  const t2r = new Map();
  for await (const t of iterCsv(join(GD, 'trips.txt'))) if (cand.has(t.route_id)) t2r.set(t.trip_id, t.route_id);
  const rStops = new Map();
  for await (const st of iterCsv(join(GD, 'stop_times.txt'))) {
    const rid = t2r.get(st.trip_id);
    if (!rid) continue;
    let s = rStops.get(rid);
    if (!s) rStops.set(rid, (s = new Set()));
    s.add(st.stop_id);
  }
  const out = []; let cut = 0;
  for (const [rid, stops] of rStops) {
    let n = 0, inside = 0, max = 0;
    for (const sid of stops) {
      const d = stopKm.get(sid);
      if (d === undefined) continue;
      n++; if (d <= coreKm) inside++; if (d > max) max = d;
    }
    if (!n || inside / n < share) continue;
    if (max > capKm) { cut++; continue; }
    out.push(rid);
  }
  out.sort();
  log(`${label}: wybrano ${out.length} (odrzucone limitem ${capKm} km: ${cut}): ${[...new Set(out.map((id) => cand.get(id)))].sort().join(', ')}`);
  return out;
}

const vbz = await select('data/gtfs-vbz', (r) => ['0', '3'].includes((r.route_type || '').trim()), 15, 0.5, 30, 'ZVV tram+bus');
const sbahn = await select('data/gtfs-ch', (r) => (r.route_type || '').trim() === '109' && /^SN?\d+$/.test((r.route_short_name || '').trim()), 25, 0.5, 55, 'S-Bahn');
writeFileSync(join(ROOT, 'data/scope.json'), JSON.stringify({ vbz, sbahn }, null, 0));
log('zapisano data/scope.json');
