import cv2
import numpy as np
import json
import os
import pytesseract
from datetime import datetime

from components.utils import get_row_boundaries, AnalysisConfig, load_and_preprocess_image
from components.shared_digit_detector import shared_detector
from components.player_template_manager import PlayerTemplateManager

# Player column position constants
PLAYER_COLUMN_X_START = 28
PLAYER_COLUMN_X_END = 308
PLAYER_ROW_HEIGHT = 80
PLAYER_IMAGE_X_START = 28
PLAYER_IMAGE_X_END = 108
PLAYER_NAME_X_START = 120
PLAYER_NAME_X_END = 300
PLAYER_NAME_Y_START = 14
PLAYER_NAME_HEIGHT = 24
PLAYER_INFO_X_START = 120
PLAYER_INFO_Y_START = 39
PLAYER_INFO_HEIGHT = 20
PLAYER_INFO_X_END = 178
PLAYER_LEVEL_X_START = 120
PLAYER_LEVEL_X_END = 140
PLAYER_GOLD_X_START = 140
PLAYER_GOLD_X_END = 160

ROWS_START_Y = 96


class PlayerExtractor:
    """Extracts player information from scoreboard rows."""
    
    def __init__(self, debug=False):
        self.template_manager = PlayerTemplateManager()
        self.debug = debug
    
    def extract_player_name_region(self, image, row_y):
        """Extract the player name region from a row."""
        name_y_start = row_y + PLAYER_NAME_Y_START
        name_y_end = name_y_start + PLAYER_NAME_HEIGHT
        name_region = image[name_y_start:name_y_end, PLAYER_NAME_X_START:PLAYER_COLUMN_X_END]
        
        print(f"extract_player_name_region: row_y={row_y}, name_y_start={name_y_start}, name_y_end={name_y_end}")
        print(f"PLAYER_NAME_X_START={PLAYER_NAME_X_START}, PLAYER_COLUMN_X_END={PLAYER_COLUMN_X_END}")
        print(f"image.shape={image.shape}")
        print(f"name_region.shape={name_region.shape}")
        # Convert to grayscale for template matching
        """ if len(name_region.shape) == 3:
            name_region_gray = cv2.cvtColor(name_region, cv2.COLOR_BGR2GRAY)
        else:
            name_region_gray = name_region """
        
        return name_region
    
    def extract_player_level_region(self, image, row_y):
        """Extract the player level region (first 30px) from a row."""
        info_y_start = row_y + PLAYER_INFO_Y_START
        info_y_end = info_y_start + PLAYER_INFO_HEIGHT
        
        # Level is in the first 30px
        level_region = image[info_y_start:info_y_end, PLAYER_LEVEL_X_START:PLAYER_LEVEL_X_END]
        
        return level_region
    
    def extract_player_gold_region(self, image, row_y):
        """Extract the player gold region (after level region) from a row."""
        info_y_start = row_y + PLAYER_INFO_Y_START
        info_y_end = info_y_start + PLAYER_INFO_HEIGHT
        
        # Gold is in the rest of the region (after first 12px)
        gold_region = image[info_y_start:info_y_end, PLAYER_GOLD_X_START:PLAYER_GOLD_X_END]
        
        return gold_region
    

    
    def extract_player_name(self, image, row_y, skip_template_if_invalid=False, level=None, gold=None):
        """Extract player name using template matching + OCR fallback. Optionally skip template creation if level/gold invalid."""
        name_region = self.extract_player_name_region(image, row_y)
        if name_region.size == 0:
            return {"player_name": "", "template_id": None, "method": "error"}
        # Try template matching first
        template_match = self.template_manager.find_player_by_template(name_region)
        if template_match:
            if self.debug:
                print(f"Found player by template: {template_match['player_name']} (confidence: {template_match['confidence']:.3f})")
            return {
                "player_name": template_match["player_name"],
                "template_id": template_match["player_id"],
                "template_path": template_match["template_path"],
                "method": "template",
                "confidence": template_match["confidence"],
                "_should_create_template": False
            }
        # Fallback to OCR
        try:
            # Preprocess for better OCR
            name_region_processed = self._preprocess_for_ocr(name_region)
            # Extract text using OCR
            player_name = pytesseract.image_to_string(name_region_processed, config='--oem 3 --psm 8').strip()
            # Only create template if both level and gold are valid
            if player_name and len(player_name) > 1:
                # If skip_template_if_invalid is True, don't create template yet
                return {
                    "player_name": player_name,
                    "template_id": None,
                    "method": "ocr_new_template",
                    "confidence": 1.0,
                    "_should_create_template": True
                }
            else:
                if self.debug:
                    print("OCR failed to extract valid player name")
                return {"player_name": "", "template_id": None, "method": "ocr_failed", "_should_create_template": False}
        except Exception as e:
            if self.debug:
                print(f"OCR error: {e}")
            return {"player_name": "", "template_id": None, "method": "error", "_should_create_template": False}
    
    def extract_player_level(self, image, row_y):
        """Extract player level using sliding digit detection."""
        level_region = self.extract_player_level_region(image, row_y)
        if level_region.size == 0:
            return 0
        digit_matches = shared_detector.find_digits_by_sliding(level_region, 'player')
        if digit_matches:
            number_result = shared_detector.reconstruct_number_from_matches(digit_matches)
            if number_result and 1 <= number_result['number'] <= 10:
                if self.debug:
                    print(f"Found level by sliding digits: {number_result['number']} (confidence: {number_result['confidence']:.3f}, digits: {number_result['digit_count']})")
                return number_result['number']
        return 0
    
    def extract_player_gold(self, image, row_y):
        """Extract player gold using sliding digit detection with OCR fallback."""
        gold_region = self.extract_player_gold_region(image, row_y)
        if gold_region.size == 0:
            return 0
        digit_matches = shared_detector.find_digits_by_sliding(gold_region, 'player')
        if digit_matches:
            number_result = shared_detector.reconstruct_number_from_matches(digit_matches)
            if number_result and 0 <= number_result['number'] <= 99:
                if self.debug:
                    print(f"Found gold by sliding digits: {number_result['number']} (confidence: {number_result['confidence']:.3f}, digits: {number_result['digit_count']})")
                return number_result['number']
        return 0
    

    
    def _convert_to_binary(self, image):
        """Convert image to binary for consistent template matching."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return binary
    
    def _preprocess_for_ocr(self, region):
        """Preprocess image region for better OCR results."""
        # Apply threshold for binary image
        _, binary = cv2.threshold(region, 127, 255, cv2.THRESH_BINARY)
        
        # Scale up for better OCR
        scaled = cv2.resize(binary, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        return scaled
    
    def _parse_level(self, text):
        """Parse level from OCR text."""
        import re
        
        # Look for patterns like "Level 5", "5", etc.
        level = 0
        
        level_match = re.search(r'(?:level\s*)?(\d+)', text.lower())
        if level_match:
            potential_level = int(level_match.group(1))
            if potential_level <= 10:  # Reasonable level range
                level = potential_level
        
        return level
    
    def _parse_gold(self, text):
        """Parse gold from OCR text."""
        import re
        gold = 0
        
        gold_matches = re.findall(r'(\d+)', text)
        for match in gold_matches:
            potential_gold = int(match)
            if potential_gold > 0 and potential_gold <= 99:  # Reasonable gold range
                gold = potential_gold
                break
        
        return gold
    
    def extract_all_player_data(self, image, row_y, row_number):
        """Extract all player data for a single row."""
        # Extract name using template matching + OCR
        name_result = self.extract_player_name(image, row_y, skip_template_if_invalid=True)
        # Extract level and gold using OCR
        level = self.extract_player_level(image, row_y)
        gold = self.extract_player_gold(image, row_y)
        # Return simplified structure
        return {
            "playerRow": row_number,
            "playerName": name_result["player_name"],
            "playerLevel": level,
            "playerGold": gold,
            "_should_create_template": name_result.get("_should_create_template", False)
        }

# Usage example
def extract_players_from_scoreboard(image, config, overlay_name_binaries=None):
    """Extract player data for all rows in the scoreboard."""
    extractor = PlayerExtractor(debug=config.debug)
    players_data = []
    row_boundaries = get_row_boundaries()
    if config.debug:
        print(f"###########################################################################################"+" player_extraction.py" + " - STARTED ")
    for row_num, row_y in enumerate(row_boundaries):
        if config.debug:
            print(f"\n--- Extracting Player Data for Row {row_num} ---")
        player_data = extractor.extract_all_player_data(image, row_y, row_num)
        # Only add if BOTH level and gold are not None (0 is valid)
        if (
            player_data["playerName"]
            and player_data["playerLevel"] is not None
            and player_data["playerGold"] is not None
        ):
            # Only create template if needed
            if player_data.get("_should_create_template"):
                overlay_binary = overlay_name_binaries[row_num] if overlay_name_binaries is not None and row_num < len(overlay_name_binaries) else None
                # Create scoreboard template and get new template_id
                template_id = extractor.template_manager.add_new_player(
                    extractor.extract_player_name_region(image, row_y),
                    player_data["playerName"],
                    template_type="scoreboard"
                )
                # Also create overlay template with the same template_id if overlay_binary is available
                if overlay_binary is not None:
                    extractor.template_manager.add_new_player(
                        overlay_binary,
                        player_data["playerName"],
                        template_type="overlay",
                        player_id=template_id
                    )
            players_data.append(player_data)
        elif config.debug:
            print(f"Skipping row {row_num} - missing valid level or gold or player name")
    if config.debug:
        print(f"###########################################################################################"+" player_extraction.py" + " - FINISHED")
    return players_data



if __name__ == "__main__":
    # Test the player extraction system
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_14.png"
    
    # Load and extract player data
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is not None:
        players_data = extract_players_from_scoreboard(image, config)
        
        print(f"\n=== EXTRACTED PLAYER DATA ===")
        for player in players_data:
            print(f"Row {player['playerRow']}: {player['playerName']} (Level {player['playerLevel']}, Gold {player['playerGold']})")
    else:
        print(f"Failed to load image: {image_path}")