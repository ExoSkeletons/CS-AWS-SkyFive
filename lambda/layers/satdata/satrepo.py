import os
from datetime import datetime, timedelta

import boto3

from satendpoints import fetch_sat_from_nasa

tle_table_name = os.environ.get('TLE_TABLE_NAME', None)

dynamodb = boto3.resource('dynamodb')


def get_tle(norad_id: int) -> tuple[str, str]:
    cache_table = dynamodb.Table(tle_table_name) if tle_table_name else None
    if cache_table is not None:
        try:
            cache_res = cache_table.get_item(Key={'norad_id': int(norad_id)})
            if 'Item' in cache_res:
                item = cache_res['Item']
                return item['line1'], item['line2']
        except RuntimeError:
            pass  # Fallback to live fetch if cache read errors out
    else:
        print('No TLE cache table name found. TLE will be fetched without caching.')

    data = fetch_sat_from_nasa(norad_id)
    line1, line2 = data['line1'], data['line2']
    name = data.get('name', None)

    if cache_table is not None:
        try:
            cache_table.put_item(Item={
                'norad_id': int(norad_id),
                'name': str(name),
                'timestamp': int(datetime.now().timestamp()),
                'expires': int((datetime.now() + timedelta(days=1)).timestamp()),
                'line1': str(line1),
                'line2': str(line2),
            })
        except RuntimeError as e:
            print(f"Error writing to cache {tle_table_name}.\n{e}")
            pass  # Don't crash the request if writing to cache fails

    return line1, line2
