import requests
import json
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import time
from io import BytesIO
import logging
import urllib.parse
import urllib.request
import sys

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Set up logging
log_filename = "logs/gastropath.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, mode='a'),
        logging.StreamHandler()
    ]
)

# Add a separator for new run
logging.info("=" * 50)
logging.info("New Gastropath run started")
logging.info("=" * 50)

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

def expand_short_url(short_url):
    try:
        response = urllib.request.urlopen(short_url)
        expanded_url = response.url
        logging.info(f"Expanded URL: {expanded_url}")
        return expanded_url
    except Exception as e:
        logging.error(f"Error expanding short URL: {e}")
        return None

def extract_place_info(url):
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    ftid = query_params.get('ftid', [None])[0]
    query = query_params.get('q', [None])[0]
    
    if not ftid or not query:
        logging.error("Could not extract necessary information from URL")
        return None, None
    return ftid, query

def get_place_details_from_google(identifier):
    logging.info(f"Getting place details for: {identifier}")
    if identifier.startswith('http'):
        expanded_url = expand_short_url(identifier)
        if not expanded_url:
            return None
        ftid, query = extract_place_info(expanded_url)
        if not ftid or not query:
            return None
    else:
        ftid = None
        query = identifier

    def make_request(url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Error making request: {e}")
            return None

    if ftid:
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": ftid,
            "fields": "name,formatted_address,website,price_level,address_component,photos,url",
            "key": GOOGLE_API_KEY
        }
        url = f"{details_url}?{urllib.parse.urlencode(details_params)}"
        data = make_request(url)
        if data and data['status'] == 'OK':
            return process_place_details(data['result'])

    find_place_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    find_place_params = {
        "input": query,
        "inputtype": "textquery",
        "fields": "place_id",
        "key": GOOGLE_API_KEY
    }
    find_place_url = f"{find_place_url}?{urllib.parse.urlencode(find_place_params)}"
    
    find_place_data = make_request(find_place_url)
    if find_place_data and find_place_data['status'] == 'OK' and find_place_data['candidates']:
        place_id = find_place_data['candidates'][0]['place_id']
        logging.info(f"Found place_id: {place_id}")
        
        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
        details_params = {
            "place_id": place_id,
            "fields": "name,formatted_address,website,price_level,address_component,photos,url",
            "key": GOOGLE_API_KEY
        }
        url = f"{details_url}?{urllib.parse.urlencode(details_params)}"
        
        data = make_request(url)
        if data and data['status'] == 'OK':
            return process_place_details(data['result'])
        else:
            logging.error(f"Place Details request failed. Status: {data['status'] if data else 'Unknown'}")
    else:
        logging.error(f"Find Place request failed. Status: {find_place_data['status'] if find_place_data else 'Unknown'}")

    logging.error("Failed to fetch restaurant information")
    return None

def process_place_details(details):
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
        "name": details.get('name', 'Unknown'),
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
        return [{"id": result["id"], "identifier": result["properties"]["Name"]["title"][0]["plain_text"]} for result in results if "Name" in result["properties"]]
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
        return False
    return True

def create_notion_entry(details, cover_url=None):
    url = f"https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {
            "database_id": NOTION_DATABASE_ID,
            "type": "database_id"
        },
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
        },
        "icon": {
            "type": "emoji",
            "emoji": "🍽️"
        }
    }
    if cover_url:
        data["cover"] = {
            "type": "external",
            "external": {
                "url": cover_url
            }
        }
    
    logging.info(f"Creating new Notion entry")
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        logging.error(f"Failed to create Notion entry: {response.status_code}, {response.text}")
        return False
    logging.info("Successfully created new Notion entry")
    return True

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
    identifier = entry["identifier"]
    logging.info(f"Processing restaurant: {identifier}")
    
    place_details = get_place_details_from_google(identifier)
    if place_details:
        try:
            cover_url = None
            if place_details.get("photo_reference"):
                cover_url = upload_image_to_cloudinary(place_details["photo_reference"])
                log_update(place_details["name"], "Cover Image", "Updated" if cover_url else "Failed to update")

            cuisine_type = get_cuisine_type_from_yelp(place_details.get("name"), place_details.get("city"))
            log_update(place_details["name"], "Cuisine Type", cuisine_type)
            place_details["cuisine_type"] = cuisine_type

            for key, value in place_details.items():
                log_update(place_details["name"], key, value)

            if "id" in entry and entry["id"] != "new_entry":
                success = update_notion_entry(entry["id"], place_details, cover_url)
            else:
                success = create_notion_entry(place_details, cover_url)

            if success:
                logging.info(f"Successfully {'updated' if 'id' in entry else 'created'} {place_details['name']} in Notion")
            else:
                logging.error(f"Failed to {'update' if 'id' in entry else 'create'} {place_details['name']} in Notion")
        except Exception as e:
            logging.error(f"Error processing {identifier}: {str(e)}")
    else:
        logging.warning(f"No details found for {identifier}")

def main(url=None):
    logging.info("Starting Gastropath update process")
    if url:
        # Process single URL
        entry = {"identifier": url}
        process_restaurant(entry)
    else:
        # Process all restaurants from Notion as before
        restaurants = get_restaurants_from_notion()
        if not restaurants:
            logging.warning("No restaurants found in Notion database.")
            return

        for restaurant in restaurants:
            process_restaurant(restaurant)

    logging.info("Gastropath update process completed")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()

