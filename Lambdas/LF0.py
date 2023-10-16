import json
import logging
import boto3
import datetime

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):
    # TODO implement
    message = event['body']
    message = json.loads(message)
    message = message["messages"]
    bot_response_message = "Please Try again!"

    if message is not None or len(message) > 0:
        session_attributes = {
            'customAttribute': message[0]['unstructured']['existingUniqueID']}
        data = message[0]['unstructured']['text']
        client = boto3.client('lex-runtime')
        bot_response = client.post_text(botName='DiningConc', botAlias='dining_bot',
                                        userId='test', inputText=data,  sessionAttributes=session_attributes)
        bot_response_message = bot_response['message']

    response = {
        'messages': [
            {
                "type": "unstructured",
                "unstructured": {
                    "id": "1",
                    "text": bot_response_message,
                    "timestamp": str(datetime.datetime.now().timestamp())
                }
            }
        ]
    }

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(response)
    }
