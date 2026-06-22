import boto3
import json
import os
from boto3.dynamodb.conditions import Key

from awsutils.api.lambda_integration import allows_cors

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['HF_TABLE_NAME'])


@allows_cors
def lambda_handler(event, context):
    user_id = event['pathParameters']['user_id']

    try:
        response = table.query(
            IndexName='ByUsers',
            KeyConditionExpression=Key('user_id').eq(str(user_id))
        )

        tracklist = [item['norad_id'] for item in response.get('Items', [])]

        return {
            'statusCode': 200,
            'body': json.dumps(tracklist)
        }

    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}