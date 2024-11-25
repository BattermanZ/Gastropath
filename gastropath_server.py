from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import subprocess
import logging
from logging.handlers import RotatingFileHandler
import re
from urllib.parse import urlparse, urlencode, parse_qs
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Set up logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'gastropath_server.log')
file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# Set up rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["5 per minute", "10 per hour"]
)

# API key
API_KEY = os.getenv("API_KEY")

def mask_api_key(key):
    if key and len(key) > 5:
        return key[:5] + '*' * (len(key) - 5)
    return key

def log_environment_variables():
    env_vars = {}
    for key, value in os.environ.items():
        if key == "API_KEY":
            env_vars[key] = mask_api_key(value)
        elif 'KEY' in key.upper():
            env_vars[key] = '*' * 8
        else:
            env_vars[key] = value
    app.logger.info(f"Environment variables: {json.dumps(env_vars, indent=2)}")

def validate_and_sanitize_url(url):
    if not url or not isinstance(url, str):
        return None, "Invalid URL format"

    if len(url) > 2000:
        return None, "URL exceeds maximum length"

    parsed_url = urlparse(url)

    if parsed_url.netloc != 'maps.app.goo.gl':
        return None, "URL is not from a trusted domain"

    if not re.match(r'^/[A-Za-z0-9]+$', parsed_url.path):
        return None, "Invalid URL path"

    query_params = parse_qs(parsed_url.query)
    allowed_params = ['g_st']
    sanitized_params = {k: v for k, v in query_params.items() if k in allowed_params}

    sanitized_url = f"https://{parsed_url.netloc}{parsed_url.path}"
    if sanitized_params:
        sanitized_url += f"?{urlencode(sanitized_params, doseq=True)}"

    return sanitized_url, None

@app.route('/add_restaurant', methods=['POST'])
@limiter.limit("5 per minute; 10 per hour")
def add_restaurant():
    request_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    app.logger.info(f"Request {request_id}: Add restaurant request received")

    try:
        headers = {k: v if 'api' not in k.lower() else '*' * 8 for k, v in request.headers.items()}
        app.logger.info(f"Request {request_id}: Headers: {json.dumps(headers, indent=2)}")

        api_key = request.headers.get('X-API-Key')
        app.logger.info(f"Request {request_id}: Received API key: {mask_api_key(api_key)}")
        app.logger.info(f"Request {request_id}: Expected API key: {mask_api_key(API_KEY)}")

        if api_key != API_KEY:
            app.logger.warning(f"Request {request_id}: Invalid API key")
            return jsonify({"error": "Invalid API key"}), 401

        data = request.json
        app.logger.info(f"Request {request_id}: Request body: {json.dumps(data, indent=2)}")

        url = data.get('URL')
        if not url:
            app.logger.warning(f"Request {request_id}: No URL provided")
            return jsonify({"error": "No URL provided"}), 400

        sanitized_url, error = validate_and_sanitize_url(url)
        if error:
            app.logger.error(f"Request {request_id}: URL validation failed: {error}")
            return jsonify({"error": error}), 400

        app.logger.info(f"Request {request_id}: Sanitized URL: {sanitized_url}")

        result = subprocess.run(['python3', 'gastropath.py', sanitized_url], capture_output=True, text=True)

        if result.returncode == 0:
            app.logger.info(f"Request {request_id}: Restaurant added successfully")
            return "Restaurant added successfully", 200
        else:
            app.logger.error(f"Request {request_id}: Error adding restaurant: {result.stderr}")
            return jsonify({
                "status": "error",
                "message": "Failed to add restaurant",
                "details": result.stderr
            }), 500

    except Exception as e:
        app.logger.error(f"Request {request_id}: Error processing add_restaurant request: {str(e)}")
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
    log_environment_variables()
    app.run(debug=True, port=9999, host='0.0.0.0')