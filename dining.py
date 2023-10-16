import requests
import random
import time
import boto3
from datetime import datetime
from decimal import Decimal
import json

api_key = ''
base_url = 'https://api.yelp.com/v3/businesses/search'
manhattan_coordinates = {'latitude': 40.7831, 'longitude': -73.9712}
cuisine_types = ['Chinese', 'Italian', 'Indian']
restaurants = []
restaurants_per_cuisine = 50

for cuisine in cuisine_types:
    restaurants_cuisine = []
    offset = 0
    while len(restaurants_cuisine) < restaurants_per_cuisine:
        params = {
            'term': cuisine + ' restaurant',
            'location': 'Manhattan',
            'limit': 50,
            'offset': offset
        }

        headers = {
            'Authorization': f'Bearer {api_key}'
        }

        response = requests.get(base_url, params=params, headers=headers)
        data = response.json()
        if 'businesses' not in data:
            break

        unique_restaurants = [r for r in data['businesses'] if r['id'] not in [
            restaurant['id'] for restaurant in restaurants_cuisine]]

        for restaurant in unique_restaurants:
            restaurant['cuisine'] = cuisine

        restaurants_cuisine.extend(unique_restaurants)
        restaurants.extend(unique_restaurants)

        offset += 50

        time.sleep(2)

    print(f'Collected {len(restaurants_cuisine)} {cuisine} restaurants')

random.shuffle(restaurants)

print(f'Total restaurants collected: {len(restaurants)}')

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('yelp-restaurants')

for restaurant in restaurants:
    item = {
        'BusinessID': restaurant['id'],
        'Name': restaurant['name'],
        'Cuisine': restaurant['cuisine'],
        'Address': restaurant['location']['address1'],
        'Coordinates': f"{restaurant['coordinates']['latitude']}, {restaurant['coordinates']['longitude']}",
        'NumberOfReviews': restaurant['review_count'],
        'Rating': Decimal(restaurant['rating']),
        'ZipCode': restaurant['location']['zip_code'],
        'insertedAtTimestamp': str(datetime.now())
    }


def print_json_format(restaurant, index_name, file):
    restaurant_id = restaurant['id']
    cuisine = restaurant['cuisine']
    output = f'{{ "index" : {{ "_index": "{index_name}", "_id" : "{restaurant_id}" }} }}\n'
    output += json.dumps({"cuisine": cuisine}, indent=None) + '\n'
    file.write(output)


index_name = "restaurants"
with open("restaurant_data_italian.json", 'w') as output_file:
    for restaurant in restaurants:
        if(restaurant["cuisine"] == "Chinese"):
            print_json_format(restaurant, index_name, output_file)

print(f'Data saved to {"restaurant_data.json"}')
