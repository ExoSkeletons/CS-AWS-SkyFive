import json
import os

import boto3

from awsutils.api.lambda_integration import allow_cors
from boto3.dynamodb.conditions import Key
from satmath import compute_current_motion
from satrepo import get_tle

admin_user_group_name = os.environ.get('ADMIN_USER_GROUP_NAME', "Admin")
table_name = os.environ.get('HF_TABLE_NAME', None)
dynamodb = boto3.resource('dynamodb')


def get_sat_info(norad_id):
    line1, line2 = get_tle(norad_id)
    motion = compute_current_motion(line1, line2)

    return {
        'norad_id': norad_id,
        'tle': [line1, line2]
    } | motion


def delete_sat_riders(norad_id):
    table = dynamodb.Table(table_name)

    batch = table.batch_writer()
    return batch.delete_item(
        KeyConditionExpression=Key('norad_id').eq(norad_id),
        ReturnValues='ALL_OLD'
    )

@allow_cors(methods=['GET', 'DELETE'])
def lambda_handler(event, context):
    norad_id = event['pathParameters']['norad_id']

    http_method = event['httpMethod']

    if http_method == 'GET':
        return {
            'statusCode': 200,
            'body': json.dumps(get_sat_info(norad_id))
        }

    if http_method == 'DELETE':
        authorizer_claims = event['requestContext']['authorizer']['claims']
        user_groups = authorizer_claims.get('cognito:groups', '')
        if admin_user_group_name not in user_groups:
           return {
               'statusCode': 403,
               # 'body': json.dumps({'error': 'Forbidden: Administrative access required.'})
           }

        return {
            'statusCode': 200,
            'body': json.dumps(delete_sat_riders(norad_id))
        }

    return {
        'statusCode': 405,
        'body': json.dumps({
            'error': 'Method not allowed'
        })
    }