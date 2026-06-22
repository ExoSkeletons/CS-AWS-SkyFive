from datetime import timezone, datetime, timedelta

import numpy as np
from geopy.distance import geodesic
from skyfield.api import load
from skyfield.framelib import itrs
from skyfield.positionlib import Geocentric
from skyfield.sgp4lib import EarthSatellite
from skyfield.toposlib import wgs84, GeographicPosition


def predict_path(
        line1, line2, norad_id,
        start_time=datetime.now(tz=timezone.utc),
        step_minutes=10, duration_hours=1
):
    ts = load.timescale(builtin=True)
    satellite = EarthSatellite(line1, line2, name=str(norad_id), ts=ts)

    total_steps = int((duration_hours * 60) / step_minutes) + 1
    path_points = []

    for step in range(total_steps + 1):
        current_time = start_time + timedelta(minutes=step * step_minutes)
        t = ts.from_datetime(current_time)
        geocentric = satellite.at(t)
        subpoint = wgs84.subpoint(geocentric)

        path_points.append({
            "timestamp_iso": current_time.isoformat(),
            "timestamp": int(current_time.timestamp()),
            "geolocation": {
                "latitude": round(float(subpoint.latitude.degrees), 4),
                "longitude": round(float(subpoint.longitude.degrees), 4),
                "altitude": round(float(subpoint.elevation.km), 2),
            },
        })
    return path_points


def compute_current_motion(line1, line2):
    ts = load.timescale(builtin=True)
    satellite = EarthSatellite(line1, line2, ts=ts)
    now = datetime.now(timezone.utc)

    geocentric: Geocentric = satellite.at(ts.from_datetime(now))
    subpoint: GeographicPosition = wgs84.subpoint(geocentric)

    orbital_speed = np.linalg.norm(geocentric.velocity.km_per_s)
    ground_speed = np.linalg.norm(geocentric.frame_xyz_and_velocity(itrs)[1].km_per_s)

    return {
        "latitude": round(float(subpoint.latitude.degrees), 4),
        "longitude": round(float(subpoint.longitude.degrees), 4),
        "altitude": round(float(subpoint.elevation.km), 2),
        "velocity": round(float(orbital_speed), 3),
        "velocity_ground": round(float(ground_speed), 3),
    }


def geodist(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    point1 = (lat1, lng1)
    point2 = (lat2, lng2)
    return geodesic(point1, point2).km
