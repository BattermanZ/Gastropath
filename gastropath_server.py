from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import subprocess
import logging
import re
from urllib.parse import urlparse, urlencode, parse_qs
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["5 per minute", "10 per hour"]
)

# API key (in a real-world scenario, use a more secure method to store and retrieve this)
API_KEY = os.getenv("API_KEY")

def validate_and_sanitize_url(url):
    if not url or not isinstance(url, str):
        return None, "Invalid URL format"

    if len(url) > 2000:
        return None, "URL exceeds maximum length"

    parsed_url = urlparse(url)

    # Check if it's a valid Google Maps short URL
    if parsed_url.netloc != 'maps.app.goo.gl':
        return None, "URL is not from a trusted domain"

    # Validate the path format (should be like /H7b33nyqkUEaTAJU7)
    if not re.match(r'^/[A-Za-z0-9]+$', parsed_url.path):
        return None, "Invalid URL path"

    # Parse and sanitize query parameters
    query_params = parse_qs(parsed_url.query)
    allowed_params = ['g_st']
    sanitized_params = {k: v for k, v in query_params.items() if k in allowed_params}

    # Reconstruct the sanitized URL
    sanitized_url = f"https://{parsed_url.netloc}{parsed_url.path}"
    if sanitized_params:
        sanitized_url += f"?{urlencode(sanitized_params, doseq=True)}"

    return sanitized_url, None

@app.route('/add_restaurant', methods=['POST'])
@limiter.limit("5 per minute; 10 per hour")
def add_restaurant():
    try:
        # Check for API key
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            return jsonify({"error": "Invalid API key"}), 401

        logging.info("Add restaurant request received")

        data = request.json
        url = data.get('URL')

        if not url:
            return jsonify({"error": "No URL provided"}), 400

        sanitized_url, error = validate_and_sanitize_url(url)
        if error:
            logging.error(f"URL validation failed: {error}")
            return jsonify({"error": error}), 400

        logging.info(f"Sanitized URL: {sanitized_url}")

        result = subprocess.run(['python3', 'gastropath.py', sanitized_url], capture_output=True, text=True)

        if result.returncode == 0:
            logging.info("Restaurant added successfully")
            return "Restaurant added successfully", 200
        else:
            logging.error(f"Error adding restaurant: {result.stderr}")
            return jsonify({
                "status": "error",
                "message": "Failed to add restaurant",
                "details": result.stderr
            }), 500

    except Exception as e:
        logging.error(f"Error processing add_restaurant request: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "details": str(e)
        }), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "status": "error",
        "message": "Rate limit exceeded. Please try again later.",
        "details": str(e)
    }), 429

if __name__ == '__main__':
    app.run(debug=True, port=9999, host='0.0.0.0')

