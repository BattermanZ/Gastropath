import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google Places API setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
YELP_API_KEY = os.getenv("YELP_API_KEY")

if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY environment variable not set.")
    exit(1)

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
                price_level = details.get('price_level', 'No price information available')
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
                    "google_maps_link": google_maps_link
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
            return ', '.join(categories) if categories else 'No cuisine information available'
        else:
            return 'No match found on Yelp'
    else:
        print(f"Failed to retrieve data from Yelp: {response.status_code}, {response.text}")
        return 'No cuisine information available'

def main():
    restaurant_name = input("Enter the name of the restaurant: ")
    place_details = get_place_details_from_google(restaurant_name)
    if place_details:
        city = place_details.get('city', 'No city available')
        cuisine_type = get_cuisine_type_from_yelp(restaurant_name, city)
        print(f"Cuisine Type: {cuisine_type}")

if __name__ == "__main__":
    main()
