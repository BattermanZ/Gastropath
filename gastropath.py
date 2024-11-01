import requests
import json
import os
from dotenv import load_dotenv

from difflib import SequenceMatcher

# Load environment variables from .env file
load_dotenv()

# Google Places API setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
YELP_API_KEY = os.getenv("YELP_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

def get_place_details_from_google(restaurant_name):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": restaurant_name,
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        results = response.json().get('results')
        if results:
            place = results[0]
            # Extracting additional details
            place_id = place.get('place_id', None)
            if not place_id:
                print(f"No place ID found for {restaurant_name}")
                return None
            
            details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
            details_params = {
                "place_id": place_id,
                "fields": "website,formatted_address,name,price_level,address_component",
                "key": GOOGLE_API_KEY
            }
            details_response = requests.get(details_url, params=details_params)
            if details_response.status_code == 200:
                details = details_response.json().get('result', {})
                website = details.get('website', 'No website available')
                price_level = details.get('price_level', '❓')
                if isinstance(price_level, int):
                    price_level = "💵" * price_level
                address_components = details.get('address_components', [])

                # Extract city from address components
                city = 'No city available'
                for component in address_components:
                    if 'locality' in component.get('types', []):
                        city = component.get('long_name')
                        break

                google_maps_link = f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else "No link available"
                
                # Print the required information
                print(f"Website: {website}")
                print(f"Price Range: {price_level}")
                print(f"City: {city}")
                print(f"Google Maps Link: {google_maps_link}")
                return {
                    "website": website,
                    "price_level": price_level,
                    "city": city,
                    "google_maps_link": google_maps_link,
                    "address": details.get('formatted_address', 'No address available')
                }
            else:
                print(f"Failed to retrieve detailed data from Google: {details_response.status_code}, {details_response.text}")
                return None
        else:
            print(f"No match found for {restaurant_name}")
            return None
    else:
        print(f"Failed to retrieve data from Google: {response.status_code}, {response.text}")
        return None

if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY environment variable not set.")
    exit(1)

# Function to retrieve all restaurants from Notion
def get_restaurants_from_notion():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        results = response.json().get("results", [])
        return [{"id": result["id"], "name": result["properties"]["Name"]["title"][0]["plain_text"]} for result in results if "Name" in result["properties"]]
    else:
        print(f"Failed to retrieve data from Notion: {response.status_code}, {response.text}")
        return []

# Function to update a restaurant entry in Notion
def update_notion_entry(entry_id, details):
    url = f"https://api.notion.com/v1/pages/{entry_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "properties": {
            "City": {
                "rich_text": [{"text": {"content": details.get("city", "❓")}}]
            },
            "Cuisine Type": {
                "rich_text": [{"text": {"content": details.get("cuisine_type", "❓")}}]
            },
            "Google Maps": {
                "url": details.get("google_maps_link", "❓")
            },
            "Price range": {
                "select": {"name": details.get("price_level", "❓")}
            },
            "Website": {
                "url": details.get("website", "❓")
            }
        }
    }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code != 200:
        print(f"Failed to update Notion entry {entry_id}: {response.status_code}, {response.text}")

def get_cuisine_type_from_yelp(restaurant_name, city):
    url = "https://api.yelp.com/v3/businesses/search"
    headers = {
        "Authorization": f"Bearer {YELP_API_KEY}"
    }
    params = {
        "term": restaurant_name,
        "location": city,
        "limit": 1
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        businesses = response.json().get('businesses')
        if businesses:
            # Take the first result and extract the categories
            business = businesses[0]
            categories = [category['title'] for category in business.get('categories', [])]
            return ', '.join(categories) if categories else '❓'
        else:
            return '❓'
    else:
        print(f"Failed to retrieve data from Yelp: {response.status_code}, {response.text}")
        return '❓'

# Function to get details from Google and Yelp, and update Notion
def process_restaurant(entry):
    restaurant_name = entry["name"]
    place_details = get_place_details_from_google(restaurant_name)
    if place_details:
        cuisine_type = get_cuisine_type_from_yelp(restaurant_name, place_details.get("city"))
    print(f"Cuisine Type: {cuisine_type}")
    place_details["cuisine_type"] = cuisine_type
    update_notion_entry(entry["id"], place_details)

def main():
    # Retrieve restaurants from Notion database
    restaurants = get_restaurants_from_notion()
    if not restaurants:
        print("No restaurants found in Notion database.")
        return

    # Process each restaurant entry
    for restaurant in restaurants:
        process_restaurant(restaurant)

if __name__ == "__main__":
    main()
