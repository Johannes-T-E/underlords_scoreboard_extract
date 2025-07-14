import cv2
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import pytesseract
from datetime import datetime

@dataclass
class ExtractionRegion:
    """Defines a region of the image for extraction"""
    x: int
    y: int
    width: int
    height: int
    column_type: str
    column_name: str

@dataclass
class PlayerRow:
    """Represents a detected player row with its regions"""
    row_index: int
    y_position: int
    height: int
    regions: List[ExtractionRegion]

class BaseColumnExtractor(ABC):
    """Base class for column extractors"""
    
    @abstractmethod
    def extract(self, image: np.ndarray, region: ExtractionRegion) -> Any:
        """Extract data from the given region"""
        pass
    
    @abstractmethod
    def validate(self, extracted_data: Any) -> bool:
        """Validate the extracted data"""
        pass

class TextColumnExtractor(BaseColumnExtractor):
    """Extracts text data (player names, etc.)"""
    
    def __init__(self, ocr_config: str = '--oem 3 --psm 8'):
        self.ocr_config = ocr_config
    
    def extract(self, image: np.ndarray, region: ExtractionRegion) -> str:
        # Extract region of interest
        roi = image[region.y:region.y+region.height, region.x:region.x+region.width]
        
        # Preprocess for better OCR
        roi = self._preprocess_text(roi)
        
        # Extract text using OCR
        text = pytesseract.image_to_string(roi, config=self.ocr_config).strip()
        return text
    
    def validate(self, extracted_data: str) -> bool:
        # Basic validation for text
        return len(extracted_data) > 0 and len(extracted_data) < 50
    
    def _preprocess_text(self, roi: np.ndarray) -> np.ndarray:
        # Convert to grayscale if needed
        if len(roi.shape) == 3:
            roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold for better OCR
        _, roi = cv2.threshold(roi, 127, 255, cv2.THRESH_BINARY)
        
        # Scale up for better OCR
        roi = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        return roi

class NumberColumnExtractor(BaseColumnExtractor):
    """Extracts numeric data (health, gold, level, etc.)"""
    
    def __init__(self, expected_range: Optional[Tuple[int, int]] = None):
        self.expected_range = expected_range
        self.ocr_config = '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789'
    
    def extract(self, image: np.ndarray, region: ExtractionRegion) -> int:
        # Extract region of interest
        roi = image[region.y:region.y+region.height, region.x:region.x+region.width]
        
        # Preprocess for numbers
        roi = self._preprocess_number(roi)
        
        # Extract text using OCR
        text = pytesseract.image_to_string(roi, config=self.ocr_config).strip()
        
        # Convert to number
        try:
            number = int(text)
            return number
        except ValueError:
            return 0  # Default value if extraction fails
    
    def validate(self, extracted_data: int) -> bool:
        if self.expected_range:
            return self.expected_range[0] <= extracted_data <= self.expected_range[1]
        return extracted_data >= 0
    
    def _preprocess_number(self, roi: np.ndarray) -> np.ndarray:
        # Convert to grayscale if needed
        if len(roi.shape) == 3:
            roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold for better OCR
        _, roi = cv2.threshold(roi, 127, 255, cv2.THRESH_BINARY)
        
        # Scale up for better OCR
        roi = cv2.resize(roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        
        return roi

class UnitColumnExtractor(BaseColumnExtractor):
    """Extracts unit information from board/bench areas"""
    
    def __init__(self, unit_templates: Dict[str, np.ndarray]):
        self.unit_templates = unit_templates  # Template images for each unit
    
    def extract(self, image: np.ndarray, region: ExtractionRegion) -> List[Dict[str, Any]]:
        # Extract region of interest
        roi = image[region.y:region.y+region.height, region.x:region.x+region.width]
        
        # Detect units using template matching
        units = self._detect_units(roi)
        
        return units
    
    def validate(self, extracted_data: List[Dict[str, Any]]) -> bool:
        # Validate unit data structure
        for unit in extracted_data:
            if 'unit_name' not in unit or 'position' not in unit:
                return False
        return True
    
    def _detect_units(self, roi: np.ndarray) -> List[Dict[str, Any]]:
        units = []
        
        # This would use template matching or other computer vision techniques
        # to identify units in the board area
        
        # Placeholder implementation
        # In reality, you'd iterate through unit templates and find matches
        
        return units

class ItemColumnExtractor(BaseColumnExtractor):
    """Extracts item information"""
    
    def __init__(self, item_templates: Dict[str, np.ndarray]):
        self.item_templates = item_templates
    
    def extract(self, image: np.ndarray, region: ExtractionRegion) -> List[Dict[str, Any]]:
        # Extract region of interest
        roi = image[region.y:region.y+region.height, region.x:region.x+region.width]
        
        # Detect items using template matching
        items = self._detect_items(roi)
        
        return items
    
    def validate(self, extracted_data: List[Dict[str, Any]]) -> bool:
        # Validate item data structure
        for item in extracted_data:
            if 'name' not in item:
                return False
        return True
    
    def _detect_items(self, roi: np.ndarray) -> List[Dict[str, Any]]:
        items = []
        
        # Template matching for items
        # Placeholder implementation
        
        return items

class ScoreboardExtractor:
    """Main class that orchestrates the extraction process"""
    
    def __init__(self):
        self.extractors = self._initialize_extractors()
        self.column_definitions = self._define_columns()
    
    def _initialize_extractors(self) -> Dict[str, BaseColumnExtractor]:
        """Initialize all column extractors"""
        return {
            'text': TextColumnExtractor(),
            'number': NumberColumnExtractor(),
            'health': NumberColumnExtractor(expected_range=(0, 100)),
            'gold': NumberColumnExtractor(expected_range=(0, 200)),
            'level': NumberColumnExtractor(expected_range=(1, 10)),
            'units': UnitColumnExtractor({}),  # Unit templates would be loaded here
            'items': ItemColumnExtractor({})   # Item templates would be loaded here
        }
    
    def _define_columns(self) -> List[Dict[str, Any]]:
        """Define the column layout for Dota Underlords scoreboard"""
        return [
            {'name': 'player_name', 'type': 'text', 'x_offset': 0, 'width': 150},
            {'name': 'level', 'type': 'level', 'x_offset': 150, 'width': 50},
            {'name': 'health', 'type': 'health', 'x_offset': 200, 'width': 80},
            {'name': 'gold', 'type': 'gold', 'x_offset': 280, 'width': 60},
            {'name': 'wins', 'type': 'number', 'x_offset': 340, 'width': 50},
            {'name': 'losses', 'type': 'number', 'x_offset': 390, 'width': 50},
            {'name': 'crew', 'type': 'units', 'x_offset': 440, 'width': 400},
            {'name': 'bench', 'type': 'units', 'x_offset': 840, 'width': 200},
            {'name': 'items', 'type': 'items', 'x_offset': 1040, 'width': 150}
        ]
    
    def extract_scoreboard(self, image_path: str) -> Dict[str, Any]:
        """Main extraction method"""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Detect player rows
        player_rows = self._detect_player_rows(image)
        
        # Extract data for each player
        players = []
        for row in player_rows:
            player_data = self._extract_player_data(image, row)
            if player_data:
                players.append(player_data)
        
        # Build final scoreboard structure
        scoreboard = {
            "metadata": {
                "round": 0,  # Would be extracted from UI
                "game_id": f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "game_mode": "unknown",
                "lobby_size": len(players),
                "current_phase": "unknown",
                "time_remaining": 0
            },
            "players": players,
            "alliances": [],  # Would be extracted from UI
            "extraction_info": {
                "confidence": self._calculate_confidence(players),
                "extraction_time": datetime.now().isoformat(),
                "errors": [],
                "partial_data": False
            }
        }
        
        return {"scoreboard": scoreboard}
    
    def _detect_player_rows(self, image: np.ndarray) -> List[PlayerRow]:
        """Detect individual player rows in the scoreboard"""
        # This would use computer vision to identify row boundaries
        # Placeholder implementation
        
        # For now, assume fixed row positions (would be detected dynamically)
        rows = []
        row_height = 60  # Approximate row height
        start_y = 100    # Start position
        
        for i in range(8):  # Max 8 players
            y_pos = start_y + (i * row_height)
            regions = []
            
            # Create extraction regions for each column
            for col_def in self.column_definitions:
                region = ExtractionRegion(
                    x=col_def['x_offset'],
                    y=y_pos,
                    width=col_def['width'],
                    height=row_height,
                    column_type=col_def['type'],
                    column_name=col_def['name']
                )
                regions.append(region)
            
            rows.append(PlayerRow(
                row_index=i,
                y_position=y_pos,
                height=row_height,
                regions=regions
            ))
        
        return rows
    
    def _extract_player_data(self, image: np.ndarray, row: PlayerRow) -> Optional[Dict[str, Any]]:
        """Extract data for a single player row"""
        player_data = {
            "player_name": "",
            "position": row.row_index + 1,
            "level": 1,
            "gold": 0,
            "health": 100,
            "max_health": 100,
            "wins": 0,
            "losses": 0,
            "net_worth": 0,
            "winstreak": 0,
            "is_eliminated": False,
            "avatar": "",
            "crew": [],
            "bench": [],
            "items": []
        }
        
        # Extract data from each column
        for region in row.regions:
            extractor = self.extractors[region.column_type]
            try:
                extracted_data = extractor.extract(image, region)
                
                # Validate extracted data
                if extractor.validate(extracted_data):
                    player_data[region.column_name] = extracted_data
                else:
                    print(f"Validation failed for {region.column_name}")
                    
            except Exception as e:
                print(f"Error extracting {region.column_name}: {e}")
        
        # Check if player row has valid data (at least has a name)
        if player_data['player_name']:
            return player_data
        
        return None
    
    def _calculate_confidence(self, players: List[Dict[str, Any]]) -> float:
        """Calculate overall extraction confidence"""
        if not players:
            return 0.0
        
        # Simple confidence based on successful extractions
        total_fields = len(players) * 9  # Approximate number of fields per player
        successful_fields = sum(1 for player in players for key, value in player.items() 
                              if value not in [None, "", 0, []])
        
        return successful_fields / total_fields if total_fields > 0 else 0.0

# Usage example
def main():
    extractor = ScoreboardExtractor()
    
    try:
        result = extractor.extract_scoreboard("screenshot03.png")
        print("Extraction successful!")
        print(f"Found {len(result['scoreboard']['players'])} players")
        print(f"Confidence: {result['scoreboard']['extraction_info']['confidence']:.2f}")
        
    except Exception as e:
        print(f"Extraction failed: {e}")

if __name__ == "__main__":
    main() 