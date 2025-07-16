# Flask backend for Dota Underlords Scoreboard
# Run with: pip install flask flask-cors && python backend_server.py
# Access API at: http://localhost:5000/api/scoreboard
# Access frontend at: http://localhost:5000/

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os

app = Flask(__name__, static_folder='.')
CORS(app)

@app.route('/api/scoreboard')
def get_scoreboard():
    path = os.path.join('output', 'scoreboard_data.json')
    if not os.path.exists(path):
        return jsonify({'error': 'scoreboard_data.json not found'}), 404
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Always sort players by row_number for frontend diffing
    if 'players' in data:
        data['players'] = sorted(data['players'], key=lambda p: p.get('row_number', 0))
    return jsonify(data)

# Serve index.html at root
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Serve static files (JS, CSS, images, etc.)
@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 