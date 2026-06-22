import json

from awsutils.api.lambda_integration import allows_cors_auth
from satrepo import get_tle
from satmath import predict_path


@allows_cors_auth
def lambda_handler(event, context):
    try:
        norad_id = event['pathParameters']['norad_id']
        query_params = event.get('queryStringParameters') or {}

        line1, line2 = get_tle(norad_id)

        duration_hours = float(query_params.get('duration_hours', 2))
        step_minutes = int(query_params.get('step_minutes', 30))

        path = predict_path(
            line1, line2, norad_id,
            step_minutes=step_minutes,
            duration_hours=duration_hours
        )

        return {'statusCode': 200, 'body': json.dumps({
            'norad_id': norad_id,
            't': duration_hours * 60, 'd': step_minutes,
            'n': len(path),
            'path': path
        })}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}