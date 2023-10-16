import time
import os
import logging
import json
import boto3
from botocore.exceptions import ClientError
import re
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def push_to_sqs(QueueURL, message, sessionAttributes):
    sqs = boto3.client('sqs', region_name='us-east-1')
    try:
        response = sqs.send_message(
            QueueUrl=QueueURL,
            DelaySeconds=0,
            MessageAttributes={
                'sessionAttributes': {
                    'DataType': 'String',
                    'StringValue': json.dumps(sessionAttributes)
                },
                'cuisine': {
                    'DataType': 'String',
                    'StringValue': message['cuisine']
                },
                'location': {
                    'DataType': 'String',
                    'StringValue': message['location']
                },
                'email': {
                    'DataType': 'String',
                    'StringValue': message['email']
                },
                'time': {
                    'DataType': 'String',
                    'StringValue': message['time']
                },
                'num_people': {
                    'DataType': 'Number',
                    'StringValue': message['num_people']
                }
            },
            MessageBody=(
                'Dining Bot'
            )
        )

    except ClientError as e:
        logging.error(e)
        return None
    return response


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def build_validation_result(is_valid, violated_slot, message_content):
    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def is_valid_email(email):
    # Regular expression pattern for a basic email format check
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    # Using re.match function to check if the email matches the pattern.
    if re.match(pattern, email):
        return True
    else:
        return False


def validate_parameters(dining_time, cuisine_type, location, num_people, email_addr):
    location_types = ['manhattan', 'new york', 'nyc']
    if not location:
        return build_validation_result(False, 'location', 'What city or city area are you looking to dine in?')

    elif location.lower() not in location_types:
        print("this is the location", location)
        return build_validation_result(False, 'location', 'Please enter a different location')

    cuisine_types = ['chinese', 'indian', 'japanese', 'italian', 'mexican']
    if not cuisine_type:
        return build_validation_result(False, 'cuisine', 'What cuisine would you like to try?')

    elif cuisine_type.lower() not in cuisine_types:
        return build_validation_result(False, 'cuisine', 'We do not have any restaurant that serves {}. Please enter a different cuisine'.format(cuisine_type))

    if not dining_time:
        return build_validation_result(False, 'time', 'What time do you prefer?')

    if not num_people:
        return build_validation_result(False, 'num_people', ' How many people are in your party?')

    if not email_addr:
        return build_validation_result(False, 'email', 'Please share your Email Address')

    elif not is_valid_email(email_addr):
        return build_validation_result(False, 'email', 'Please enter the correct Email Address'.format(email_addr))

    return build_validation_result(True, None, None)


def get_restaurants(intent_request):
    dynamodb = boto3.resource('dynamodb')
    table2 = dynamodb.Table("users-pastData")
    user = table2.query(KeyConditionExpression=Key('id').eq(
        intent_request['sessionAttributes']['customAttribute']))
    user = user.get('Items', {})
    source = intent_request['invocationSource']
    if source == 'DialogCodeHook':
        slots = get_slots(intent_request)
        print(slots)
        time_ = slots["time"]
        cuisine = slots["cuisine"]
        location = slots["location"]
        num_people = slots["num_people"]
        email_addr = slots["email"]
        prev_rec = slots["prev_rec"]

        if(user):
            if(prev_rec == "yes"):
                location = ""+user[0]["location"]
                print("location from db", location)
                cuisine = ""+user[0]["cuisine"]
                print("cuisine from db", cuisine)

        slot_dict = {
            'time': time_,
            'cuisine': cuisine,
            'location': location,
            'num_people': num_people,
            'email': email_addr
        }

        validation_result = validate_parameters(
            time_, cuisine, location, num_people, email_addr)
        print(validation_result)
        if not validation_result['isValid']:
            if user:
                if not prev_rec:
                    validation_result = build_validation_result(
                        False, 'prev_rec', 'Do you want to use your previous search criteria? Reply by typing yes or no')
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

    res = push_to_sqs('https://sqs.us-east-1.amazonaws.com/540009924757/myqueue',
                      slot_dict, intent_request['sessionAttributes'])
    print("res", res)
    print(slot_dict)
    if res:
        response = {
            "dialogAction":
            {
                "fulfillmentState": "Fulfilled",
                "type": "Close",
                "message":
                {
                    "contentType": "PlainText",
                    "content": "You're all set! Expect my recommendations at {} for your group of {} to dine at {} in {}!".format(
                                    email_addr, num_people, time_, location),
                }
            }
        }
    else:
        response = {
            "dialogAction":
            {
                "fulfillmentState": "Fulfilled",
                "type": "Close",
                "message":
                {
                    "contentType": "PlainText",
                    "content": "Sorry, come back after some time!",
                }
            }
        }
    return response


def dispatch(event):
    logger.debug('dispatch userId={}, intentName={}'.format(
        event['userId'], event['currentIntent']['name']))
    intent_name = event['currentIntent']['name']
    if intent_name == 'DiningSuggestionsIntent':
        return get_restaurants(event)
    raise Exception('Intent with name ' + intent_name + ' not supported')


def lambda_handler(event, context):
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)
