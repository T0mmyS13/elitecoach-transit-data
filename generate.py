"""Build a small regional GTFS snapshot from public datasets, without user data.

Usage: python generate.py [--output PATH] [--bbox S,W,N,E]
The selected region is deployment data coverage, not an athlete's itinerary.
"""
import argparse
import csv
import gzip
import io
import json
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

FEEDS = [
    ("pmdp", "https://jizdnirady.pmdp.cz/jr/gtfs", "PMDP · CC-BY-4.0", "https://opendata.plzen.eu/public/opendata/detail/187"),
    ("jdf", "https://motis.obehy.cz/get-feeds/cz-jdf-filtered-gtfs.zip", "JDF → GTFS · CC0-1.0", "https://github.com/public-transport/transitous/blob/main/feeds/cz.json"),
]


def rows(archive, name):
    if name not in archive.namelist():
        return
    with archive.open(name) as raw:
        yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"))


def seconds(value):
    h, m, s = map(int, value.split(":"))
    return h * 3600 + m * 60 + s


def build(output, bbox):
    south, west, north, east = bbox
    snapshot = {"generatedAt": datetime.now(timezone.utc).isoformat(), "bbox": bbox,
                "stops": {}, "trips": {}, "calendar": {}, "exceptions": {}, "sources": []}
    for prefix, url, attribution, license_url in FEEDS:
        print(f"Downloading public timetable: {prefix}", flush=True)
        request = urllib.request.Request(url, headers={"User-Agent": "Public transit snapshot (https://github.com/T0mmyS13/elitecoach-transit-data)"})
        with tempfile.TemporaryFile() as file:
            with urllib.request.urlopen(request, timeout=60) as response:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > 100 * 1024 * 1024:
                        raise ValueError("GTFS download exceeds size limit")
                    file.write(chunk)
            file.seek(0)
            with zipfile.ZipFile(file) as archive:
                if sum(item.file_size for item in archive.infolist()) > 1500 * 1024 * 1024:
                    raise ValueError("GTFS expansion exceeds size limit")
                local_stops = {}
                for row in rows(archive, "stops.txt"):
                    lat, lon = float(row["stop_lat"]), float(row["stop_lon"])
                    if south <= lat <= north and west <= lon <= east and row.get("location_type", "0") in ("", "0"):
                        local_stops[row["stop_id"]] = [row["stop_name"], lat, lon]
                routes = {r["route_id"]: r.get("route_short_name") or r.get("route_long_name") or r["route_id"] for r in rows(archive, "routes.txt")}
                trips = {r["trip_id"]: [prefix + ":" + r["service_id"], routes.get(r["route_id"], ""), []] for r in rows(archive, "trips.txt")}
                for row in rows(archive, "stop_times.txt"):
                    if row["stop_id"] not in local_stops or row["trip_id"] not in trips:
                        continue
                    if not row.get("arrival_time") or not row.get("departure_time"):
                        continue
                    trips[row["trip_id"]][2].append([int(row["stop_sequence"]), prefix + ":" + row["stop_id"],
                        seconds(row["arrival_time"]), seconds(row["departure_time"]),
                        row.get("pickup_type", "0") in ("", "0"), row.get("drop_off_type", "0") in ("", "0")])
                for trip_id, trip in trips.items():
                    if len(trip[2]) >= 2:
                        trip[2].sort(key=lambda item: item[0])
                        snapshot["trips"][prefix + ":" + trip_id] = trip
                snapshot["stops"].update({prefix + ":" + key: value for key, value in local_stops.items()})
                for row in rows(archive, "calendar.txt"):
                    snapshot["calendar"][prefix + ":" + row["service_id"]] = [row["start_date"], row["end_date"],
                        [int(row[day]) for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")]]
                for row in rows(archive, "calendar_dates.txt"):
                    snapshot["exceptions"].setdefault(prefix + ":" + row["service_id"], {})[row["date"]] = int(row["exception_type"])
        snapshot["sources"].append({"name": attribution, "url": url, "licenseUrl": license_url})
        print(f"Imported {len(snapshot['stops'])} stops, {len(snapshot['trips'])} trips", flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as stream:
        json.dump(snapshot, stream, ensure_ascii=False, separators=(",", ":"))
    temporary.replace(output)
    print(f"Saved {output.name} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "transit.json.gz")
    parser.add_argument("--bbox", default="49.55,12.8,50.25,13.8")
    args = parser.parse_args()
    build(args.output, list(map(float, args.bbox.split(","))))
