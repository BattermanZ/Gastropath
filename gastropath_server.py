from flask import Flask
import subprocess

app = Flask(__name__)

@app.route('/run_gastropath', methods=['POST'])
def run_gastropath():
    try:
        # Run your existing Python script
        subprocess.Popen(['python3', 'gastropath.py'])
        return "Gastropath script triggered successfully!", 200
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True, port=9999, host='0.0.0.0')
