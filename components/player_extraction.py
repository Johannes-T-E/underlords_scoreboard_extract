import cv2
import numpy as np
import json
import os
import pytesseract
from datetime import datetime

# Player column position constants
PLAYER_COLUMN_X_START = 28
PLAYER_COLUMN_X_END = 308
PLAYER_ROW_HEIGHT = 80
PLAYER_IMAGE_X_START = 28
PLAYER_IMAGE_X_END = 108
PLAYER_NAME_X_START = 120
PLAYER_NAME_Y_START = 14
NAME_HEIGHT = 24
PLAYER_INFO_X_START = 120
PLAYER_INFO_Y_START = 39
PLAYER_INFO_HEIGHT = 20
PLAYER_INFO_X_END = 178
ROWS_START_Y = 96


class DigitDetector:
    """Detects individual digits (0-9) using sliding window detection."""
    
    def __init__(self, templates_dir="assets/templates/digits"):
        self.templates_dir = templates_dir
        self.digit_templates = {}  # Will store single template per digit (0-9)
        
        # Create directories if they don't exist
        os.makedirs(templates_dir, exist_ok=True)
        
        # Load existing digit templates
        self._load_digit_templates()
    
    def _load_digit_templates(self):
        """Load existing digit templates from disk."""
        import glob
        
        # Find all digit template files (both formats)
        template_files = glob.glob(os.path.join(self.templates_dir, "digit_*.png"))
        template_files.extend(glob.glob(os.path.join(self.templates_dir, "[0-9].png")))
        
        for template_file in template_files:
            filename = os.path.basename(template_file)
            
            # Parse filename to extract digit value
            # Supports both: digit_5.png and 5.png
            import re
            match = re.match(r'digit_(\d)\.png', filename)
            if not match:
                match = re.match(r'(\d)\.png', filename)
            
            if match:
                digit_value = int(match.group(1))
                
                # Load template
                template = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    # Convert to binary and store (single template per digit)
                    self.digit_templates[digit_value] = self._convert_to_binary(template)
    
    def _convert_to_binary(self, image):
        """Convert image to binary for consistent template matching."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return binary
    
    def find_digits_by_sliding(self, number_region, confidence_threshold=0.95):
        """Find all digits in a region using sliding window detection."""
        if number_region.size == 0:
            return []
        
        number_region_binary = self._convert_to_binary(number_region)
        matches = []
        
        # For each digit (0-9)
        for digit_value, template in self.digit_templates.items():
            # Get template dimensions
            template_height, template_width = template.shape
            
            # Skip if template is larger than the region
            if template_height > number_region_binary.shape[0] or template_width > number_region_binary.shape[1]:
                continue
            
            # Slide the template horizontally across the region
            for x in range(number_region_binary.shape[1] - template_width + 1):
                # Extract sub-region at position x
                sub_region = number_region_binary[:template_height, x:x+template_width]
                
                # Resize template to match sub-region if needed
                if template.shape != sub_region.shape:
                    template_resized = cv2.resize(template, (sub_region.shape[1], sub_region.shape[0]))
                else:
                    template_resized = template
                
                # Template matching
                result = cv2.matchTemplate(sub_region, template_resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                # If good match found
                if max_val >= confidence_threshold:
                    matches.append({
                        'digit': digit_value,
                        'x_position': x,
                        'confidence': max_val,
                        'width': template_width
                    })
        
        return matches
    
    def reconstruct_number_from_matches(self, matches):
        """Reconstruct a number from positioned digit matches."""
        if not matches:
            return None
        
        # Sort matches by x position (left to right)
        sorted_matches = sorted(matches, key=lambda m: m['x_position'])
        
        # Remove overlapping matches (keep highest confidence)
        filtered_matches = []
        for match in sorted_matches:
            # Check if this match overlaps with any existing match
            overlaps = False
            for existing in filtered_matches:
                # Check for overlap
                if (match['x_position'] < existing['x_position'] + existing['width'] and
                    match['x_position'] + match['width'] > existing['x_position']):
                    # Overlap detected, keep the one with higher confidence
                    if match['confidence'] > existing['confidence']:
                        filtered_matches.remove(existing)
                        break
                    else:
                        overlaps = True
                        break
            
            if not overlaps:
                filtered_matches.append(match)
        
        # Sort again after filtering
        filtered_matches.sort(key=lambda m: m['x_position'])
        
        # Reconstruct number
        if not filtered_matches:
            return None
        
        number_str = ''.join(str(match['digit']) for match in filtered_matches)
        
        try:
            number = int(number_str)
            avg_confidence = sum(match['confidence'] for match in filtered_matches) / len(filtered_matches)
            
            return {
                'number': number,
                'confidence': avg_confidence,
                'digit_count': len(filtered_matches)
            }
        except ValueError:
            return None
    




class PlayerTemplateManager:
    """Manages player name templates for fast recognition."""
    
    def __init__(self, templates_dir="assets/templates/players", players_db="assets/players_database.json"):
        self.templates_dir = templates_dir
        self.players_db_path = players_db
        self.players_db = self._load_players_database()
        self.templates_cache = {}
        
        # Create directories if they don't exist
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(os.path.dirname(players_db), exist_ok=True)
    
    def _load_players_database(self):
        """Load the players database from JSON."""
        if os.path.exists(self.players_db_path):
            try:
                with open(self.players_db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Return default structure
        return {
            "next_template_id": 1,
            "players": {}
        }
    
    def _save_players_database(self):
        """Save the players database to JSON."""
        with open(self.players_db_path, 'w', encoding='utf-8') as f:
            json.dump(self.players_db, f, indent=2, ensure_ascii=False)
    
    def _load_template(self, template_id):
        """Load a template image from disk."""
        if template_id in self.templates_cache:
            return self.templates_cache[template_id]
        
        template_path = os.path.join(self.templates_dir, f"player_{template_id:03d}.png")
        if os.path.exists(template_path):
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            self.templates_cache[template_id] = template
            return template
        
        return None
    
    def _save_template(self, name_image, player_name):
        """Save a new template and update database."""
        template_id = self.players_db["next_template_id"]
        template_path = os.path.join(self.templates_dir, f"player_{template_id:03d}.png")
        
        # Convert to binary (black and white) for better template matching
        name_image_binary = self._convert_to_binary(name_image)
        
        # Save template image
        cv2.imwrite(template_path, name_image_binary)
        
        # Update database
        self.players_db["players"][str(template_id)] = {
            "name": player_name,
            "template_path": template_path,
            "created_at": datetime.now().isoformat(),
            "usage_count": 1
        }
        self.players_db["next_template_id"] += 1
        
        # Cache the template
        self.templates_cache[template_id] = name_image_binary
        
        # Save database
        self._save_players_database()
        
        return template_id

    def _convert_to_binary(self, image):
        """Convert image to binary (black and white) for consistent template matching."""
        # Ensure grayscale first
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply binary threshold
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        return binary

    def find_player_by_template(self, name_image, threshold=0.99):
        """Try to find player by template matching."""
        # Convert input image to binary
        name_image_binary = self._convert_to_binary(name_image)
        
        best_match = None
        best_confidence = 0.0
        
        for template_id_str, player_info in self.players_db["players"].items():
            template_id = int(template_id_str)
            template = self._load_template(template_id)
            
            if template is None:
                continue
            
            # Ensure template is also binary (in case of legacy templates)
            template_binary = self._convert_to_binary(template)
            
            # Resize template to match name_image if needed
            if template_binary.shape != name_image_binary.shape:
                template_resized = cv2.resize(template_binary, (name_image_binary.shape[1], name_image_binary.shape[0]))
            else:
                template_resized = template_binary
            
            # Template matching
            result = cv2.matchTemplate(name_image_binary, template_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            if max_val > best_confidence:
                best_confidence = max_val
                best_match = {
                    "template_id": template_id,
                    "player_name": player_info["name"],
                    "confidence": max_val
                }
        
        # Return match if above threshold
        if best_match and best_confidence >= threshold:
            # Update usage count
            template_id_str = str(best_match["template_id"])
            self.players_db["players"][template_id_str]["usage_count"] += 1
            self._save_players_database()
            return best_match
        
        return None
    
    def add_new_player(self, name_image, player_name):
        """Add a new player template."""
        template_id = self._save_template(name_image, player_name)
        return {
            "template_id": template_id,
            "player_name": player_name,
            "confidence": 1.0
        }
    
    def get_all_players(self):
        """Get list of all known players."""
        return [(info["name"], int(template_id)) for template_id, info in self.players_db["players"].items()]

class PlayerExtractor:
    """Extracts player information from scoreboard rows."""
    
    def __init__(self, debug=False):
        self.template_manager = PlayerTemplateManager()
        self.digit_detector = DigitDetector()
        self.debug = debug
    
    def extract_player_name_region(self, image, row_y):
        """Extract the player name region from a row."""
        name_y_start = row_y + PLAYER_NAME_Y_START
        name_y_end = name_y_start + NAME_HEIGHT
        
        name_region = image[name_y_start:name_y_end, PLAYER_NAME_X_START:PLAYER_COLUMN_X_END]
        
        # Convert to grayscale for template matching
        if len(name_region.shape) == 3:
            name_region_gray = cv2.cvtColor(name_region, cv2.COLOR_BGR2GRAY)
        else:
            name_region_gray = name_region
        
        return name_region_gray
    
    def extract_player_info_region(self, image, row_y):
        """Extract the player info region (level/gold) from a row."""
        info_y_start = row_y + PLAYER_INFO_Y_START
        info_y_end = info_y_start + PLAYER_INFO_HEIGHT
        
        info_region = image[info_y_start:info_y_end, PLAYER_INFO_X_START:PLAYER_INFO_X_END]
        
        return info_region
    
    def extract_player_level_region(self, image, row_y):
        """Extract the player level region (first 30px) from a row."""
        info_y_start = row_y + PLAYER_INFO_Y_START
        info_y_end = info_y_start + PLAYER_INFO_HEIGHT
        
        # Level is in the first 30px
        level_region = image[info_y_start:info_y_end, PLAYER_INFO_X_START:PLAYER_INFO_X_START + 20]
        
        return level_region
    
    def extract_player_gold_region(self, image, row_y):
        """Extract the player gold region (after level region) from a row."""
        info_y_start = row_y + PLAYER_INFO_Y_START
        info_y_end = info_y_start + PLAYER_INFO_HEIGHT
        
        # Gold is in the rest of the region (after first 12px)
        gold_region = image[info_y_start:info_y_end, PLAYER_INFO_X_START + 24:PLAYER_INFO_X_END]
        
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
                "template_id": template_match["template_id"],
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
        
        # Try sliding digit detection using shared detector
        try:
            from components.shared_digit_detector import shared_detector
            
            # Find all digit matches using sliding window
            digit_matches = shared_detector.find_digits_by_sliding(level_region, 'player')
            
            if digit_matches:
                # Reconstruct number from digit matches
                number_result = shared_detector.reconstruct_number_from_matches(digit_matches)
                
                if number_result and number_result['number'] >= 1 and number_result['number'] <= 10:
                    if self.debug:
                        print(f"Found level by sliding digits: {number_result['number']} (confidence: {number_result['confidence']:.3f}, digits: {number_result['digit_count']})")
                    return number_result['number']
        except ImportError:
            # Fallback to old method
            digit_matches = self.digit_detector.find_digits_by_sliding(level_region)
            
            if digit_matches:
                # Reconstruct number from digit matches
                number_result = self.digit_detector.reconstruct_number_from_matches(digit_matches)
                
                if number_result and number_result['number'] >= 1 and number_result['number'] <= 10:
                    if self.debug:
                        print(f"Found level by sliding digits: {number_result['number']} (confidence: {number_result['confidence']:.3f}, digits: {number_result['digit_count']})")
                    return number_result['number']
        
        # Fallback to OCR
        """ try:
            level_region_processed = self._preprocess_for_ocr(level_region)
            level_text = pytesseract.image_to_string(level_region_processed, config='--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789').strip()
            level = self._parse_level(level_text)
            
            if self.debug:
                print(f"Extracted level by OCR: {level} from text: '{level_text}'")
            
            return level
            
        except Exception as e:
            if self.debug:
                print(f"Level OCR error: {e}")
            return 0 """
    
    def extract_player_gold(self, image, row_y):
        """Extract player gold using sliding digit detection with OCR fallback."""
        gold_region = self.extract_player_gold_region(image, row_y)
        
        if gold_region.size == 0:
            return 0
        
        # Try sliding digit detection using shared detector
        try:
            from components.shared_digit_detector import shared_detector
            
            # Find all digit matches using sliding window
            digit_matches = shared_detector.find_digits_by_sliding(gold_region, 'player')
            
            if digit_matches:
                # Reconstruct number from digit matches
                number_result = shared_detector.reconstruct_number_from_matches(digit_matches)
                
                if number_result and number_result['number'] >= 0 and number_result['number'] <= 99:
                    if self.debug:
                        print(f"Found gold by sliding digits: {number_result['number']} (confidence: {number_result['confidence']:.3f}, digits: {number_result['digit_count']})")
                    return number_result['number']
        except ImportError:
            # Fallback to old method
            digit_matches = self.digit_detector.find_digits_by_sliding(gold_region)
            
            if digit_matches:
                # Reconstruct number from digit matches
                number_result = self.digit_detector.reconstruct_number_from_matches(digit_matches)
                
                if number_result and number_result['number'] >= 0 and number_result['number'] <= 99:
                    if self.debug:
                        print(f"Found gold by sliding digits: {number_result['number']} (confidence: {number_result['confidence']:.3f}, digits: {number_result['digit_count']})")
                    return number_result['number']
        
        # Fallback to OCR
        """ try:
            gold_region_processed = self._preprocess_for_ocr(gold_region)
            gold_text = pytesseract.image_to_string(gold_region_processed, config='--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789').strip()
            gold = self._parse_gold(gold_text)
            
            if self.debug:
                print(f"Extracted gold by OCR: {gold} from text: '{gold_text}'")
            
            return gold
            
        except Exception as e:
            if self.debug:
                print(f"Gold OCR error: {e}")
            return 0 """
    

    
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
def extract_players_from_scoreboard(image, config):
    """Extract player data for all rows in the scoreboard."""
    extractor = PlayerExtractor(debug=config.debug)
    players_data = []
    try:
        from utils import get_row_boundaries
    except ImportError:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils import get_row_boundaries
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
                extractor.template_manager.add_new_player(
                    extractor.extract_player_name_region(image, row_y),
                    player_data["playerName"]
                )
            players_data.append(player_data)
        elif config.debug:
            print(f"Skipping row {row_num} - missing valid level or gold or player name")
    if config.debug:
        print(f"###########################################################################################"+" player_extraction.py" + " - FINISHED")
    return players_data



if __name__ == "__main__":
    # Test the player extraction system
    try:
        from utils import AnalysisConfig, load_and_preprocess_image
    except ImportError:
        # If running from components folder, add parent directory to path
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils import AnalysisConfig, load_and_preprocess_image
    
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_07.png"
    
    # Load and extract player data
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is not None:
        players_data = extract_players_from_scoreboard(image, config)
        
        print(f"\n=== EXTRACTED PLAYER DATA ===")
        for player in players_data:
            print(f"Row {player['playerRow']}: {player['playerName']} (Level {player['playerLevel']}, Gold {player['playerGold']})")
    else:
        print(f"Failed to load image: {image_path}")