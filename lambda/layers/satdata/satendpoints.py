import os
from typing import Any

import requests

NASA_API_URL = os.environ.get('NASA_API_URL', "https://tle.ivanstanojevic.me/api/tle")
ZENITH_API_URL = os.environ.get('ZENITH_API_URL', "https://zenithapi.space/api/v1/satellites")


def fetch_sat_from_nasa(norad_id: int, api_key=None)->dict[str, Any]:
    url = f"{NASA_API_URL}/{norad_id}"
    headers = {
        'User-Agent': 'tle-fetch',
        'Accept-Encoding': 'gzip, deflate',
        'Accept': 'application/json',
        'Connection': 'keep-alive',
        'Info-ApiKey': str(api_key) if api_key else None,
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data


def fetch_nearby_from_zenith(longitude: float, latitude: float):
    url = (
        f"{ZENITH_API_URL}/nearby?"
        f"latitude={latitude}&"
        f"longitude={longitude}&"
        f"mode=extended"
    )
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    satellites = data['satellites']

    transformed = [{
        'norad_id': s['noradId'],
        'name': s['name'],
        'location': {
            'latitude': s['geoposition']['latitude'],
            'longitude': s['geoposition']['longitude'],
            'altitude': s['altitude'],
        }
    } for s in satellites]

    return transformed

# london_pos = (51.507351, -0.127758)
# print(json.dumps(
#     fetch_nearby_from_zenith(
#         latitude=london_pos[0],
#         longitude=london_pos[1]
#     ),
#     indent=4
# ))
