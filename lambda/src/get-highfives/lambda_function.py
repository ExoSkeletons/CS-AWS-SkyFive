import json
import os

import boto3
from awsutils.api.lambda_integration import allows_cors_auth
from awsutils.lambdas.parsing import DynamoJSONEncoder as dbEnc
from boto3.dynamodb.conditions import Key

table_name = os.environ.get('HIGHFIVES_TABLE_NAME', None)
cognito_arn = os.environ.get('COGNITOUSERPOOL_USER_POOL_ARN', None)
db = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')


def get_by_giver(giver_id: str) -> list:
    table = db.Table(table_name)
    return table.query(
        IndexName='GiverIndex',
        KeyConditionExpression=Key('giver_id').eq(giver_id),
        ScanIndexForward=False  # Return newest first
    ).get('Items', [])


def get_by_receiver(receiver_id: str) -> list:
    table = db.Table(table_name)
    return table.query(
        IndexName='ReceiverIndex',
        KeyConditionExpression=Key('receiver_id').eq(receiver_id),
        ScanIndexForward=False  # Return newest first
    ).get('Items', [])


@allows_cors_auth
def lambda_handler(event, context):
    try:
        auth_claims = event['requestContext']['authorizer']['claims']
        user_id = auth_claims['sub']

        resource_path = event['resource']
        action = resource_path.split('/')[-1]

        # get user pair items from db
        if not table_name:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Missing HF table name'})
            }
        if "give" in action:
            items = get_by_giver(user_id)
            items = [
                {
                    'user_id': item['receiver_id'],
                    'user_profile': item.get('receiver_profile', {}),
                    'norad_id': int(item['norad_id']),
                    'timestamp': int(item['timestamp']),
                } for item in items
            ]
        elif "rec" in action:
            items = get_by_receiver(user_id)
            items = [
                {
                    'user_id': item['giver_id'],
                    'user_profile': item.get('giver_profile', {}),
                    'norad_id': int(item['norad_id']),
                    'timestamp': int(item['timestamp']),
                } for item in items
            ]
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Could not resolve HF filter. Unsupported path: {resource_path}"})
            }

        # sort
        items = list(sorted(items, key=lambda k: k['timestamp'], reverse=True))

        return {
            "statusCode": 200,
            "body": json.dumps(items, cls=dbEnc)
        }
    except Exception as e:
        print(f"Error in HF lookup: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
