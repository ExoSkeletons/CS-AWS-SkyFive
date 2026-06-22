import json

from awsutils.api.lambda_integration import allows_cors_auth
from satendpoints import fetch_nearby_from_zenith
from satmath import geodist


@allows_cors_auth
def lambda_handler(event, context):
    query_params = event['queryStringParameters'] or {}
    latitude = float(query_params['latitude'])
    longitude = float(query_params['longitude'])
    radius_km = float(query_params.get('radius', 500))

    nearby = fetch_nearby_from_zenith(latitude=latitude, longitude=longitude)

    nearby = list(filter(
        lambda item: \
            geodist(
                lng1=item['location']['longitude'], lat1=item['location']['latitude'],
                lng2=longitude, lat2=latitude
            ) <= radius_km,
        nearby
    ))

    return {
        'statusCode': 200,
        'body': json.dumps({
            'satellites': nearby
        })
    }
