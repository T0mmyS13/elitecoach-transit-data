# Regional public transit snapshots

Public timetables for Plzeň and the surrounding region, including Žlutice, Manětín and Toužim. This repository contains only the standalone public-data generator and its refresh workflow. It contains no athlete profiles, calendars, private addresses, application credentials or coaching application source.

The `transit-data` release provides a compressed JSON snapshot used for offline journey planning. Data is refreshed each Sunday at 15:17 UTC, with manual refresh available in Actions. Preparation runs ahead of evening consumers; upstream failures preserve the previous asset. Live delays are not included.

Sources and attribution:

- PMDP / City of Plzeň: [GTFS open data](https://opendata.plzen.eu/public/opendata/detail/187), CC BY 4.0.
- Regional JDF converted to GTFS: [Transitous feed registry](https://github.com/public-transport/transitous/blob/main/feeds/cz.json), CC0.

Run `python generate.py` with Python 3.12+. The generator uses the standard library only. The coverage bounding box is a public regional coverage area, not an individual itinerary.
