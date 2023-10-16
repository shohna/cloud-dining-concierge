import random
import logging
import boto3
import json
from botocore.exceptions import ClientError
import requests
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def get_sqs_data():
    sqs = boto3.client('sqs', region_name='us-east-1')
    queue_URL = sqs.get_queue_url(QueueName="myqueue")
    print("queue", queue_URL)
    try:
        response = sqs.receive_message(
            QueueUrl=queue_URL['QueueUrl'],
            AttributeNames=['All'],
            MessageAttributeNames=['All'],
            VisibilityTimeout=0,
            WaitTimeSeconds=0
        )
        print("response", response)
        messages = response['Messages'][0]['MessageAttributes']
        receiptHandle = response['Messages'][0]['ReceiptHandle']
        sqs.delete_message(
            QueueUrl=queue_URL['QueueUrl'], ReceiptHandle=receiptHandle)
        return messages

    except ClientError as e:
        logging.error(e)
        return []


def lambda_handler(event, context):
    print(event)
    sqs_url = 'https://sqs.us-east-1.amazonaws.com/540009924757/myqueue'
    es_host = 'https://search-dining-es-ogz7pvompabqcedjjmdpaxizsi.us-east-1.es.amazonaws.com'
    index = "restaurants"
    dynamodb = boto3.resource('dynamodb')
    dbClient = boto3.client('dynamodb')
    sesClient = boto3.client('ses', region_name='us-east-1')
    table = dynamodb.Table("yelp-restaurants")
    table2 = dynamodb.Table("users-pastData")
    username = ""
    password = ""
    message_body = get_sqs_data()
    cuisine = message_body["cuisine"]["StringValue"]
    search_query = {"query": {"bool": {"must": [{"match": {"cuisine": cuisine}}], "must_not": [
    ], "should": []}}, "from": 0, "size": 50, "sort": [], "aggs": {}}
    search_url = f"{es_host}/{index}/_search"

    try:
        res = requests.post(search_url, json=search_query,
                            auth=(username, password))
        if res.status_code == 200:
            data = res.json()
            hits = data["hits"]["hits"]
            business_id = [hit['_id'] for hit in hits]
            random.shuffle(business_id)
            res0 = table.query(KeyConditionExpression=Key(
                'BusinessID').eq(business_id[0]))
            res1 = table.query(KeyConditionExpression=Key(
                'BusinessID').eq(business_id[1]))
            res2 = table.query(KeyConditionExpression=Key(
                'BusinessID').eq(business_id[2]))
            item0 = res0.get('Items', {})
            item1 = res1.get('Items', {})
            item2 = res2.get('Items', {})

            session_attributes = message_body['sessionAttributes']
            session_attributes_json = json.loads(
                session_attributes['StringValue'])
            print("userID", message_body['sessionAttributes'])

            userData = table2.put_item(
                Item={
                    'id': session_attributes_json["customAttribute"],
                    'location': message_body["location"]["StringValue"],
                    'cuisine': message_body["cuisine"]["StringValue"]
                }
            )

            emailText = """Hello! Here are my %s restaurant suggestions for %s people, at %s: \n1. %s, located at %s \n2. %s, located at %s \n3. %s, located at %s.\nEnjoy your meal!""" % (
                cuisine, message_body["num_people"]["StringValue"], message_body["time"]["StringValue"], item0[0]["Name"], item0[0]["Address"], item1[0]["Name"], item1[0]["Address"], item2[0]["Name"], item2[0]["Address"])
            print(emailText)
            sesClient.send_email(
                Destination={'ToAddresses': [
                    message_body["email"]["StringValue"]]},
                Message={'Body': {'Text': {'Data': emailText}},
                         'Subject': {'Data': 'Restaurant recommendations'}
                         },
                Source='sk11239@nyu.edu')
    except Exception as e:
        print(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Error"})
        }
