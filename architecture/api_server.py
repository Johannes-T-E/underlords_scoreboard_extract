from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
from scoreboard_extractor import ScoreboardExtractor

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Initialize the extractor
extractor = ScoreboardExtractor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/extract', methods=['POST'])
def extract_scoreboard():
    """Extract scoreboard data from uploaded image"""
    try:
        # Check if file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        # Check if file is valid
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"temp_screenshot_{timestamp}.png"
        filepath = os.path.join('temp', filename)
        
        # Create temp directory if it doesn't exist
        os.makedirs('temp', exist_ok=True)
        
        file.save(filepath)
        
        # Extract scoreboard data
        result = extractor.extract_scoreboard(filepath)
        
        # Clean up temporary file
        os.remove(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract/file', methods=['POST'])
def extract_from_file():
    """Extract scoreboard data from file path"""
    try:
        data = request.get_json()
        
        if not data or 'file_path' not in data:
            return jsonify({'error': 'No file path provided'}), 400
        
        file_path = data['file_path']
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Extract scoreboard data
        result = extractor.extract_scoreboard(file_path)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/schema', methods=['GET'])
def get_schema():
    """Get the expected data structure schema"""
    try:
        with open('scoreboard_data_structure.json', 'r') as f:
            schema = json.load(f)
        return jsonify(schema)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/config', methods=['GET'])
def get_config():
    """Get extractor configuration"""
    try:
        config = {
            'column_definitions': extractor.column_definitions,
            'available_extractors': list(extractor.extractors.keys()),
            'supported_formats': ['png', 'jpg', 'jpeg', 'bmp'],
            'max_file_size': '10MB'
        }
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/config/columns', methods=['PUT'])
def update_column_config():
    """Update column configuration"""
    try:
        data = request.get_json()
        
        if not data or 'columns' not in data:
            return jsonify({'error': 'No column configuration provided'}), 400
        
        # Update column definitions
        extractor.column_definitions = data['columns']
        
        return jsonify({
            'message': 'Column configuration updated successfully',
            'columns': extractor.column_definitions
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/regions', methods=['POST'])
def debug_regions():
    """Debug endpoint to visualize extraction regions"""
    try:
        data = request.get_json()
        
        if not data or 'file_path' not in data:
            return jsonify({'error': 'No file path provided'}), 400
        
        file_path = data['file_path']
        
        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Load image and detect rows
        import cv2
        image = cv2.imread(file_path)
        player_rows = extractor._detect_player_rows(image)
        
        # Convert to JSON-serializable format
        debug_info = []
        for row in player_rows:
            row_info = {
                'row_index': row.row_index,
                'y_position': row.y_position,
                'height': row.height,
                'regions': []
            }
            
            for region in row.regions:
                region_info = {
                    'x': region.x,
                    'y': region.y,
                    'width': region.width,
                    'height': region.height,
                    'column_type': region.column_type,
                    'column_name': region.column_name
                }
                row_info['regions'].append(region_info)
            
            debug_info.append(row_info)
        
        return jsonify({
            'image_dimensions': {
                'width': image.shape[1],
                'height': image.shape[0]
            },
            'detected_rows': debug_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('temp', exist_ok=True)
    
    # Run the server
    app.run(debug=True, host='0.0.0.0', port=5000) 