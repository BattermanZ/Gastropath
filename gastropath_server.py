from flask import Flask, request, jsonify
import subprocess
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/trigger', methods=['GET'])
def trigger_gastropath():
    try:
        logging.info("Gastropath script trigger attempted")
        subprocess.Popen(['python3', 'gastropath.py'])
        logging.info("Gastropath script triggered successfully")
        return "Gastropath script triggered successfully!", 200
    except Exception as e:
        logging.error(f"Error triggering Gastropath script: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/add_restaurant', methods=['POST'])
def add_restaurant():
    try:
        logging.info("Add restaurant request received")
        data = request.json
        url = data.get('URL')

        if not url:
            logging.error("No URL provided in the request")
            return jsonify({"error": "No URL provided"}), 400

        logging.info(f"Received URL: {url}")

        # Run the Gastropath script with the URL as an argument
        result = subprocess.run(['python3', 'gastropath.py', url], capture_output=True, text=True)

        if result.returncode == 0:
            logging.info("Restaurant processing completed successfully")
            return jsonify({"message": "Restaurant processed successfully", "details": result.stdout}), 200
        else:
            logging.error(f"Error processing restaurant: {result.stderr}")
            return jsonify({"error": "Failed to process restaurant", "details": result.stderr}), 500

    except Exception as e:
        logging.error(f"Error processing add_restaurant request: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=9999, host='0.0.0.0')

