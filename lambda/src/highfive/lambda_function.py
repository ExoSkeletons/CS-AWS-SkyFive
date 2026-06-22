import json
import os
from datetime import datetime, timedelta

import boto3
from awsutils.api.lambda_integration import allow_cors_auth
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
sns = boto3.resource('sns')

user_table = dynamodb.Table(os.environ['HF_TABLE_NAME'])
hf_table = dynamodb.Table(os.environ['HIGHFIVES_TABLE_NAME'])
topic = sns.Topic(os.environ['SNSTOPICSATEVENTS_TOPIC_ARN'])


@allow_cors_auth(methods=['POST', 'PUT'])
def lambda_handler(event, context):
    user_id = None
    body = {}
    auth_claims = {}
    try:
        query_params = event.get('queryStringParameters', {})
        user_id = query_params['user_id']
        print(user_id)
    except Exception:
        pass
    if not user_id:
        try:
            body_str = event.get('body', None) or '{}'
            if event.get('isBase64Encoded', False):
                import base64
                body_str = base64.b64decode(body_str).decode('utf-8')
            body = json.loads(body_str) if isinstance(body_str, str) else (body_str or {})

            auth_claims = event['requestContext']['authorizer']['claims']

            user_id = auth_claims['sub']
        except Exception:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Could not get User Id'})
            }

    try:
        norad_id = int(event['pathParameters']['norad_id'])

        response = user_table.query(
            KeyConditionExpression=Key('norad_id').eq(norad_id)
        )
        items = response['Items'] if 'Items' in response else []

        for item in items:
            if item['user_id'] == user_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'User already offering on this satellite.'})
                }

        for item in items:
            target_id = item['user_id']

            target_profile = item.get('user_profile', {})

            giver_profile = {
                'sub': user_id,
                'nickname': auth_claims['nickname'],
                'email': auth_claims['email'],
            }

            if 'from' in body:
                giver_profile['from'] = body['from']

            notify_user(giver_profile, target_profile, norad_id)

            update_db(
                giver_id=user_id, receiver_id=target_id, norad_id=norad_id,
                giver_profile=giver_profile, receiver_profile=target_profile,
            )

        notified = [
            {
                'user_id': item['user_id']
            } for item in items
        ]

        return {
            'statusCode': 200,
            'body': json.dumps({
                'norad_id': norad_id,
                'user_id': user_id,
                'notified': notified,
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def notify_user(giver_profile, target_profile, norad_id):
    giver_id = giver_profile.get('sub', None)
    giver_nickname = giver_profile.get('nickname', 'A startstruck observer')
    giver_email = giver_profile.get('email', None)

    target_id = target_profile.get('sub', None)
    target_nickname = target_profile.get('nickname', 'A curious sat traveller')
    target_email = target_profile.get('email', None)

    sat_name = "A Sat"  # sat_info.get('sat_name', 'A satallite')
    sat_id = norad_id  # sat_info.get('norad_id', None)

    msg = {
        "text": f"{giver_nickname}-{giver_email} just gave you ({target_nickname}-{target_email}) a HighFive across {sat_name}:{sat_id}!",
        "giver": giver_profile,
        "target": target_profile,
        "norad_id": sat_id
    }
    response = topic.publish(
        Message=json.dumps(msg),
        Subject='HighFive',
    )
    return response


def update_db(
        giver_id: str, receiver_id: str,
        giver_profile: dict, receiver_profile: dict,
        norad_id: int,
):
    # update user on sat
    response = user_table.update_item(
        Key={'norad_id': norad_id, 'user_id': receiver_id},
        UpdateExpression="SET hits = hits + :h, hitsTtl = if_not_exists(hitsTtl, :d) - :h, lastHitTimestamp = :now",
        ExpressionAttributeValues={
            ':h': 1,  # Hits to step by
            ':d': 1,  # Default value if no hitsTtl
            ':now': int(datetime.now().timestamp())
        },
        ReturnValues='UPDATED_NEW'
    )
    # remove 0 ttl records
    hits_ttl = response.get('Attributes', {}).get('hitsTtl', 0)
    if hits_ttl <= 0:
        user_table.delete_item(Key={'norad_id': norad_id, 'user_id': receiver_id})

    # update hf records
    hf_table.put_item(
        Item={
            'giver_id': str(giver_id),
            'giver_profile': giver_profile,
            'receiver_id': str(receiver_id),
            'receiver_profile': receiver_profile,

            'norad_id': int(norad_id),

            'timestamp': int(datetime.now().timestamp()),
            'expires': int((datetime.now() + timedelta(days=3)).timestamp()),
        }
    )

    # table.delete_item(Key={'user_id': user_id, 'norad_id': norad_id})
