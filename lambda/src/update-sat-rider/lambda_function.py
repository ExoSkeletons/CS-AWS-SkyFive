import json
import os
import time

import boto3
from awsutils.api.lambda_integration import allow_cors_auth

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['HF_TABLE_NAME'])
ADMIN_GROUP = os.environ['ADMIN_USER_GROUP_NAME']
PAID_GROUP = os.environ.get('PAID_USER_GROUP_NAME', None)


def is_riding(norad_id: int, user_id: str):
    response = table.get_item(
        Key={'norad_id': norad_id, 'user_id': user_id}
    )
    return 'Item' in response


def ride_sat(user_id: str, norad_id: int, user_profile: dict = None, hitsTtl: int = None):
    timestamp = int(time.time())
    ttl_in_days = 2

    table.put_item(
        Item={
            'norad_id': int(norad_id),
            'user_id': str(user_id),
            'user_profile': user_profile or {},

            'timestamp': timestamp,
            'ttl': timestamp + 60 * 60 * 24 * ttl_in_days,

            'hits': 0,
            'hitsTtl': int(hitsTtl) if hitsTtl else 1,
            'lastHitTimestamp': None,
        }
    )
    return {'norad_id': norad_id, 'user_id': user_id}


def leave_sat(user_id: str, norad_id: int):
    table.delete_item(
        Key={'norad_id': norad_id, 'user_id': user_id},
        ReturnValues='ALL_OLD'
    )
    return {'user_id': user_id, 'norad_id': norad_id}


@allow_cors_auth(methods=["POST", "PUT", "DELETE"])
def lambda_handler(event, context):
    norad_id = int(event['pathParameters']['norad_id'])

    try:
        auth_claims = event['requestContext']['authorizer']['claims']

        user_id = auth_claims['sub']
        user_groups = auth_claims.get('cognito:groups', [])
        if isinstance(user_groups, str): user_groups = user_groups.split(',')

        profile = {
            # 'sub': str(user_id),
            'email': str(auth_claims['email']),
            'nickname': str(auth_claims.get('nickname', 'Anonymous')),
            'username': str(auth_claims['cognito:username']),
        }
        is_admin = ADMIN_GROUP is not None and ADMIN_GROUP in user_groups
        is_paid = PAID_GROUP is not None and PAID_GROUP in user_groups
    except KeyError as e:
        return {
            'statusCode': 401,
            'body': json.dumps({'error': f"Unauthorized: Missing user auth information {e}"})
        }

    try:
        method = event['httpMethod']
        if method == 'POST' or method == 'PUT':
            if is_riding(norad_id=norad_id, user_id=user_id):
                return {
                    'statusCode': 400,
                    'body': json.dumps({'message': f"Already riding sat {norad_id}"})
                }
            res = ride_sat(
                user_id=user_id, norad_id=norad_id,
                user_profile=profile,
                hitsTtl=99 if is_admin else 3 if is_paid else 1,
            )
            return {'statusCode': 200, 'body': json.dumps(res)}
        if method == 'DELETE':
            if not is_riding(norad_id=norad_id, user_id=user_id):
                return {
                    'statusCode': 400,
                    'body': json.dumps({'message': f"Not riding sat {norad_id}"})
                }
            res = leave_sat(user_id=user_id, norad_id=norad_id)
            return {'statusCode': 200, 'body': json.dumps(res)}

        return {'statusCode': 400, 'body': 'Invalid Method'}
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)})
        }
