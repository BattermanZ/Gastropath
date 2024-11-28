# Gastropath

Gastropath is an automated restaurant database updater that integrates information from Google Maps and Yelp into a Notion database. It streamlines the process of cataloging and managing restaurant information for food enthusiasts, critics, or anyone maintaining a personal dining database.

## Features

- Extracts restaurant details from Google Maps URLs
- Retrieves additional information from Google Places API
- Fetches cuisine types from Yelp API
- Uploads restaurant images to Cloudinary
- Creates or updates entries in a Notion database
- Supports single restaurant additions
- Provides a Flask-based API server for easy integration

## Prerequisites

- Python 3.9 or higher
- Docker (for containerized deployment)

## Installation

1. Clone the repository:

2. Install required packages: pip install -r requirements.txt

3. Set up environment variables:
Create a `.env` file in the project root and add the following variables:
GOOGLE_API_KEY=your_google_api_key
YELP_API_KEY=your_yelp_api_key
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
API_KEY=your_custom_api_key_for_gastropath_server


## API Endpoints

- `POST /add_restaurant`
- Adds a new restaurant to the Notion database
- Requires `X-API-Key` header for authentication
- Request body: `{ "URL": "https://maps.app.goo.gl/example" }`

## Main Components

- `gastropath.py`: Core script for processing restaurant information
- `gastropath_server.py`: Flask server for handling API requests
- `get_template_id.py`: Utility script for retrieving Notion database template IDs

## Configuration

### Notion Database Structure

Ensure your Notion database has the following properties:
- Name (title)
- City (text)
- Country (text)
- Cuisine Type (text)
- Google Maps (URL)
- Price range (select)
- Website (URL)

### Rate Limiting

The server implements rate limiting to prevent abuse:
- 5 requests per minute
- 10 requests per hour

## Logging

Logs are stored in the `logs` directory:
- `gastropath.log`: Main application log
- `gastropath_server.log`: Server log

## Error Handling

The application includes error handling for:
- Invalid API keys
- Failed API requests
- Invalid URL formats

## Security Considerations

- API keys are stored as environment variables
- Input URLs are validated and sanitized
- HTTPS is recommended for production deployments

## Acknowledgments

- Google Places API
- Yelp Fusion API
- Notion API
- Cloudinary
- Flask and Flask-Limiter


## Disclaimer

This project is licensed under the GNU Affero General Public License (AGPL) - see the [LICENSE](LICENSE) file for details.

This project is not affiliated with Google, Yelp, Notion, or Cloudinary. Use of their APIs is subject to their respective terms of service.