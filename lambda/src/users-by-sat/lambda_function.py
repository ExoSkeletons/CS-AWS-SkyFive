import json
import boto3
from boto3.dynamodb.conditions import Key
import os

from awsutils.api.lambda_integration import allows_cors

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['HF_TABLE_NAME'])

@allows_cors
def lambda_handler(event, context):
    norad_id = int(event['pathParameters']['norad_id'])

    response = table.query(
        KeyConditionExpression=Key('norad_id').eq(norad_id)
    )
    items = response.get('Items', [])
    travellers = [
        {
            'norad_id': int(item['norad_id']),
            'user_id': str(item['user_id']),
            'hits': int(item['hits']),  # Decimal isn't dumpable so convert to int
        } | item['user_profile']
        for item in items
    ]
    return {
        'statusCode': 200,
        'body': json.dumps(travellers)
    }