# Dota Underlords Scoreboard Extractor

A modular system for extracting scoreboard information from Dota Underlords screenshots, designed to provide complete data for frontend UI recreation.

## Features

- **Modular Architecture**: Separate extractors for different column types (text, numbers, units, items)
- **Table-Based Processing**: Treats scoreboard as rows (players) and columns (data types)
- **OCR Integration**: Uses Tesseract for text and number extraction
- **Computer Vision**: Template matching for units and items
- **REST API**: Flask-based API for frontend integration
- **Validation**: Multi-level data validation and confidence scoring
- **Debug Tools**: Visualization of extraction regions for debugging

## Architecture

```
Scoreboard Extractor
├── Core Components
│   ├── ScoreboardExtractor (Main orchestrator)
│   ├── TextColumnExtractor (OCR for text)
│   ├── NumberColumnExtractor (OCR for numbers)
│   ├── UnitColumnExtractor (Computer vision for units)
│   └── ItemColumnExtractor (Computer vision for items)
├── API Server
│   ├── Flask REST API
│   ├── File upload handling
│   └── Debug endpoints
└── Data Structure
    ├── Comprehensive JSON schema
    ├── Player data with units and items
    └── Extraction metadata
```

## Installation

### Prerequisites

- Python 3.7+
- Tesseract OCR
- OpenCV dependencies

### Install Tesseract

**Windows:**
```bash
# Download and install from: https://github.com/UB-Mannheim/tesseract/wiki
# Add to PATH
```

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### 1. Basic Extraction

```python
from scoreboard_extractor import ScoreboardExtractor

# Initialize extractor
extractor = ScoreboardExtractor()

# Extract from screenshot
result = extractor.extract_scoreboard("screenshot03.png")

# Access player data
players = result['scoreboard']['players']
confidence = result['scoreboard']['extraction_info']['confidence']
```

### 2. API Server

Start the Flask server:
```bash
python api_server.py
```

The API will be available at `http://localhost:5000`

### 3. API Endpoints

#### Extract from uploaded file
```bash
POST /extract
Content-Type: multipart/form-data
Body: image file
```

#### Extract from file path
```bash
POST /extract/file
Content-Type: application/json
Body: {"file_path": "path/to/screenshot.png"}
```

#### Get data schema
```bash
GET /schema
```

#### Get configuration
```bash
GET /config
```

#### Debug regions
```bash
POST /debug/regions
Content-Type: application/json
Body: {"file_path": "path/to/screenshot.png"}
```

## Data Structure

The extracted data follows this structure:

```json
{
  "scoreboard": {
    "metadata": {
      "round": 15,
      "game_id": "unique_game_identifier",
      "timestamp": "2024-01-01T12:00:00Z",
      "game_mode": "ranked",
      "lobby_size": 8,
      "current_phase": "combat",
      "time_remaining": 30
    },
    "players": [
      {
        "player_name": "Juniper",
        "position": 1,
        "level": 7,
        "gold": 32,
        "health": 51,
        "max_health": 100,
        "wins": 18,
        "losses": 7,
        "net_worth": 192,
        "winstreak": 3,
        "is_eliminated": false,
        "crew": [...],
        "bench": [...],
        "items": [...]
      }
    ],
    "extraction_info": {
      "confidence": 0.95,
      "extraction_time": "2024-01-01T12:00:00Z",
      "errors": [],
      "partial_data": false
    }
  }
}
```

## Configuration

### Column Definitions

Modify the column layout in `scoreboard_extractor.py`:

```python
def _define_columns(self):
    return [
        {'name': 'player_name', 'type': 'text', 'x_offset': 0, 'width': 150},
        {'name': 'level', 'type': 'level', 'x_offset': 150, 'width': 50},
        {'name': 'health', 'type': 'health', 'x_offset': 200, 'width': 80},
        # ... more columns
    ]
```

### Extractor Configuration

Customize extractors with different parameters:

```python
def _initialize_extractors(self):
    return {
        'text': TextColumnExtractor(ocr_config='--oem 3 --psm 8'),
        'health': NumberColumnExtractor(expected_range=(0, 100)),
        'gold': NumberColumnExtractor(expected_range=(0, 200)),
        # ... more extractors
    }
```

## Column Types

### Text Columns
- **Used for**: Player names, text fields
- **Method**: OCR with text preprocessing
- **Configuration**: OCR mode and page segmentation

### Number Columns
- **Used for**: Health, gold, level, wins, losses
- **Method**: OCR with number-only whitelist
- **Configuration**: Expected value ranges for validation

### Unit Columns
- **Used for**: Board and bench units
- **Method**: Template matching and computer vision
- **Configuration**: Unit template images

### Item Columns
- **Used for**: Items and equipment
- **Method**: Template matching for item icons
- **Configuration**: Item template images

## Debugging

### Visualize Extraction Regions

Use the debug endpoint to see where the extractor is looking:

```bash
curl -X POST http://localhost:5000/debug/regions \
  -H "Content-Type: application/json" \
  -d '{"file_path": "screenshot03.png"}'
```

### Confidence Scoring

The system provides confidence scores to help identify extraction issues:

- **Per-field validation**: Each extractor validates its own data
- **Row-level validation**: Checks if row has minimum required data
- **Overall confidence**: Percentage of successfully extracted fields

## Customization

### Adding New Column Types

1. Create a new extractor class inheriting from `BaseColumnExtractor`
2. Implement `extract()` and `validate()` methods
3. Add to the extractor dictionary in `_initialize_extractors()`
4. Update column definitions to use the new extractor

### Template Management

For units and items, you'll need to provide template images:

```python
unit_templates = {
    'pudge': cv2.imread('templates/units/pudge.png'),
    'ogre_magi': cv2.imread('templates/units/ogre_magi.png'),
    # ... more units
}
```

## Performance Tips

1. **Image Preprocessing**: Optimize image quality before extraction
2. **Region Sizing**: Adjust region sizes for better OCR accuracy
3. **Template Quality**: Use high-quality templates for unit/item matching
4. **Parallel Processing**: Consider parallel extraction for multiple columns

## Troubleshooting

### Common Issues

1. **OCR Accuracy**: Adjust preprocessing parameters or OCR configuration
2. **Column Alignment**: Update column definitions to match your resolution
3. **Template Matching**: Ensure template images match game graphics
4. **API Errors**: Check file paths and permissions

### Error Handling

The system includes comprehensive error handling:
- Graceful degradation when extraction fails
- Detailed error reporting for debugging
- Default values for missing data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details 