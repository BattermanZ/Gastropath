# Gastropath

Gastropath is an automated restaurant database updater that integrates information from Google Maps and Yelp into a Notion database. It streamlines the process of cataloging and managing restaurant information for food enthusiasts, critics, or anyone maintaining a personal dining database.
It can be coupled with an iOS shortcut for easy updating directly from the Google Maps app.

## Features

- Extracts restaurant details from Google Maps URLs
- Retrieves additional information from Google Places API
- Fetches cuisine types from Yelp API
- Uploads restaurant images to Cloudinary
- Creates or updates entries in a Notion database
- Supports single restaurant additions
- Provides an Actix-based API server for easy integration

## Prerequisites

- Rust 1.82.0 or higher
- Docker (for containerized deployment)

## Installation

1. Clone the repository: git clone [https://github.com/yourusername/gastropath.git](https://github.com/yourusername/gastropath.git)
cd gastropath

2. Build the project: cargo build --release

3. Set up environment variables:
Create a `.env` file in the project root and add the following variables:
GOOGLE_API_KEY=your_google_api_key
YELP_API_KEY=your_yelp_api_key
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
API_KEY=your_generated_api_key_for_authentication


## API Endpoints

- `POST /add_restaurant`
- Adds a new restaurant to the Notion database
- Request body: `{ "url": "https://maps.app.goo.gl/example" }`

## Main Components

- `main.rs`: Entry point and server setup
- `google_places.rs`: Handles Google Places API interactions
- `yelp.rs`: Manages Yelp API requests
- `notion.rs`: Handles Notion database operations
- `cloudinary.rs`: Manages image uploads to Cloudinary
- `utils.rs`: Utility functions
- `logging.rs`: Logging configuration

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
- 5 requests per second
- 10 requests burst

## Logging

Logs are stored in the `logs` directory:
- `gastropath.log`: Application log

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
- Actix web framework

## Disclaimer

This project is licensed under the GNU Affero General Public License (AGPL) - see the [LICENSE](LICENSE) file for details.

This project is not affiliated with Google, Yelp, Notion, or Cloudinary. Use of their APIs is subject to their respective terms of service.

