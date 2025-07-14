# Scoreboard Extractor Architecture

## Overview
The scoreboard extractor is designed with a modular architecture that separates concerns and makes it easy to handle different types of data extraction from a Dota Underlords scoreboard.

## Core Design Principles

### 1. **Separation of Concerns**
- Each column type has its own specialized extractor
- Data extraction is separate from data validation
- Image processing is separate from business logic

### 2. **Table-Based Processing**
- Scoreboard is treated as a table: rows = players, columns = different data types
- Each row is processed independently
- Each column uses the appropriate extraction method

### 3. **Extensibility**
- Easy to add new column types by creating new extractors
- Column definitions are configurable
- Template-based approach for visual elements

## Architecture Components

```
ScoreboardExtractor (Main Orchestrator)
├── Column Extractors (Specialized processors)
│   ├── TextColumnExtractor (OCR for text)
│   ├── NumberColumnExtractor (OCR for numbers)
│   ├── UnitColumnExtractor (Computer vision for units)
│   └── ItemColumnExtractor (Computer vision for items)
├── Data Classes (Structure definitions)
│   ├── ExtractionRegion (Image regions)
│   └── PlayerRow (Row data)
└── Validation Layer (Data quality checks)
```

## Processing Flow

### 1. **Image Loading**
```python
image = cv2.imread(image_path)
```

### 2. **Row Detection**
```python
player_rows = self._detect_player_rows(image)
```
- Identifies each player row in the scoreboard
- Creates extraction regions for each column
- Returns structured row data

### 3. **Column Extraction**
```python
for region in row.regions:
    extractor = self.extractors[region.column_type]
    extracted_data = extractor.extract(image, region)
```
- Each column uses its specialized extractor
- Extractors handle preprocessing and data extraction
- Validation ensures data quality

### 4. **Data Assembly**
```python
scoreboard = {
    "metadata": {...},
    "players": players,
    "alliances": [...],
    "extraction_info": {...}
}
```

## Column Extractor Types

### TextColumnExtractor
- **Purpose**: Extract player names and text fields
- **Method**: OCR with text preprocessing
- **Preprocessing**: Grayscale conversion, thresholding, scaling
- **Validation**: Length and character validation

### NumberColumnExtractor
- **Purpose**: Extract numeric values (health, gold, level, etc.)
- **Method**: OCR with number-only whitelist
- **Preprocessing**: Enhanced contrast, scaling
- **Validation**: Range validation based on expected values

### UnitColumnExtractor
- **Purpose**: Extract unit information from board/bench
- **Method**: Template matching and computer vision
- **Templates**: Pre-stored unit images for matching
- **Validation**: Unit data structure validation

### ItemColumnExtractor
- **Purpose**: Extract item information
- **Method**: Template matching for item icons
- **Templates**: Pre-stored item images for matching
- **Validation**: Item data structure validation

## Configuration and Customization

### Column Definitions
```python
self.column_definitions = [
    {'name': 'player_name', 'type': 'text', 'x_offset': 0, 'width': 150},
    {'name': 'level', 'type': 'level', 'x_offset': 150, 'width': 50},
    # ... more columns
]
```

### Extractor Configuration
```python
self.extractors = {
    'text': TextColumnExtractor(),
    'number': NumberColumnExtractor(),
    'health': NumberColumnExtractor(expected_range=(0, 100)),
    'gold': NumberColumnExtractor(expected_range=(0, 200)),
    # ... more extractors
}
```

## Error Handling and Validation

### Multi-Level Validation
1. **Extraction Level**: Each extractor validates its own data
2. **Row Level**: Checks if row has minimum required data
3. **Scoreboard Level**: Overall confidence calculation

### Error Recovery
- Graceful degradation when extraction fails
- Default values for missing data
- Detailed error reporting for debugging

### Confidence Scoring
```python
def _calculate_confidence(self, players: List[Dict[str, Any]]) -> float:
    # Calculate based on successful extractions
    return successful_fields / total_fields
```

## Advantages of This Architecture

### 1. **Modularity**
- Easy to modify individual extractors without affecting others
- New column types can be added without changing core logic

### 2. **Testability**
- Each extractor can be tested independently
- Mock data can be used for unit testing

### 3. **Maintainability**
- Clear separation of concerns
- Well-defined interfaces between components

### 4. **Scalability**
- Easy to add new game modes or UI layouts
- Template-based approach for visual elements

### 5. **Debugging**
- Detailed error reporting at each level
- Confidence scoring helps identify problem areas

## Usage Example

```python
# Initialize extractor
extractor = ScoreboardExtractor()

# Process screenshot
result = extractor.extract_scoreboard("screenshot03.png")

# Access extracted data
players = result['scoreboard']['players']
confidence = result['scoreboard']['extraction_info']['confidence']
```

## Future Enhancements

1. **Dynamic Row Detection**: Use computer vision to detect row boundaries
2. **Template Management**: System for loading and managing unit/item templates
3. **UI Element Detection**: Extract metadata from UI elements
4. **Multi-Resolution Support**: Handle different screen resolutions
5. **Performance Optimization**: Parallel processing for multiple columns 