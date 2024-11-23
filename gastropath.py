import requests
import json
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import time
from io import BytesIO
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# API credentials
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
YELP_API_KEY = os.getenv("YELP_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Set up Cloudinary configuration
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

def log_update(restaurant_name, field, value):
    logging.info(f"Updating {restaurant_name} - {field}: {value}")

def get_place_details_from_google(restaurant_name):
    # First, perform a Text Search to get the place_id
    search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    search_params = {
        "query": restaurant_name,
        "key": GOOGLE_API_KEY
    }
    search_response = requests.get(search_url, params=search_params)
    if search_response.status_code != 200:
        logging.error(f"Failed to retrieve data from Google: {search_response.status_code}, {search_response.text}")
        return None

    search_results = search_response.json().get('results', [])
    if not search_results:
        logging.warning(f"No match found for {restaurant_name}")
        return None

    place_id = search_results[0].get('place_id')
    if not place_id:
        logging.warning(f"No place ID found for {restaurant_name}")
        return None

    # Now, use the place_id to get detailed information
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    details_params = {
        "place_id": place_id,
        "fields": "name,formatted_address,website,price_level,address_component,photos,url",
        "key": GOOGLE_API_KEY
    }
    details_response = requests.get(details_url, params=details_params)
    if details_response.status_code != 200:
        logging.error(f"Failed to retrieve detailed data from Google: {details_response.status_code}, {details_response.text}")
        return None

    details = details_response.json().get('result', {})
    
    website = details.get('website', 'No website available')
    price_level = details.get('price_level', '❓')
    if isinstance(price_level, int):
        price_level = "💵" * price_level
    address_components = details.get('address_components', [])

    city = 'No city available'
    country = 'No country available'
    for component in address_components:
        if 'locality' in component.get('types', []):
            city = component.get('long_name')
        if 'country' in component.get('types', []):
            country = component.get('long_name')

    google_maps_link = details.get('url', "No link available")

    photo_reference = None
    if details.get('photos'):
        photo_reference = details['photos'][0]['photo_reference']

    return {
        "name": details.get('name', restaurant_name),
        "website": website,
        "price_level": price_level,
        "city": city,
        "country": country,
        "google_maps_link": google_maps_link,
        "address": details.get('formatted_address', 'No address available'),
        "photo_reference": photo_reference
    }

def upload_image_to_cloudinary(photo_reference):
    if not photo_reference:
        return None

    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_reference}&key={GOOGLE_API_KEY}"
    response = requests.get(photo_url, stream=True)
    if response.status_code == 200:
        try:
            upload_result = cloudinary.uploader.upload(
                BytesIO(response.content),
                api_key=CLOUDINARY_API_KEY,
                api_secret=CLOUDINARY_API_SECRET,
                cloud_name=CLOUDINARY_CLOUD_NAME
            )
            return upload_result.get('secure_url')
        except Exception as e:
            logging.error(f"Failed to upload image to Cloudinary: {str(e)}")
            return None
    else:
        logging.error(f"Failed to retrieve photo from Google: {response.status_code}, {response.text}")
        return None

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
        return [{"id": result["id"], "name": result["properties"]["Name"]["title"][0]["plain_text"][:-1]} for result in results if "Name" in result["properties"] and result["properties"]["Name"]["title"][0]["plain_text"].endswith(';')]
    else:
        logging.error(f"Failed to retrieve data from Notion: {response.status_code}, {response.text}")
        return []

def update_notion_entry(entry_id, details, cover_url=None):
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
            "Country": {
                "rich_text": [{"text": {"content": details.get("country", "❓")}}]
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
            },
            "Name": {
                "title": [{"text": {"content": details.get("name", "❓")}}]
            }
        }
    }
    if cover_url:
        data["cover"] = {
            "type": "external",
            "external": {
                "url": cover_url
            }
        }
    response = requests.patch(url, headers=headers, json=data)
    if response.status_code != 200:
        logging.error(f"Failed to update Notion entry {entry_id}: {response.status_code}, {response.text}")

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
            business = businesses[0]
            categories = [category['title'] for category in business.get('categories', [])]
            return ', '.join(categories) if categories else '❓'
        else:
            return '❓'
    else:
        logging.error(f"Failed to retrieve data from Yelp: {response.status_code}, {response.text}")
        return '❓'

def process_restaurant(entry):
    restaurant_name = entry["name"].rstrip(';')
    logging.info(f"Processing restaurant: {restaurant_name}")
    
    try:
        place_details = get_place_details_from_google(restaurant_name)
        if place_details:
            cover_url = None
            if place_details.get("photo_reference"):
                cover_url = upload_image_to_cloudinary(place_details["photo_reference"])
                log_update(restaurant_name, "Cover Image", "Updated" if cover_url else "Failed to update")

            cuisine_type = get_cuisine_type_from_yelp(place_details.get("name"), place_details.get("city"))
            log_update(restaurant_name, "Cuisine Type", cuisine_type)
            place_details["cuisine_type"] = cuisine_type

            for key, value in place_details.items():
                log_update(restaurant_name, key, value)

            update_notion_entry(entry["id"], place_details, cover_url)
            logging.info(f"Successfully updated {restaurant_name} in Notion")
        else:
            logging.warning(f"No details found for {restaurant_name}")
    except Exception as e:
        logging.error(f"Error processing {restaurant_name}: {str(e)}")

def main():
    logging.info("Starting Gastropath update process")
    restaurants = get_restaurants_from_notion()
    if not restaurants:
        logging.warning("No restaurants found in Notion database.")
        return

    for restaurant in restaurants:
        process_restaurant(restaurant)

    logging.info("Gastropath update process completed")

if __name__ == "__main__":
    main()

