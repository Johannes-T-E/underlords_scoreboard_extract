import cv2
import numpy as np
import os
import glob
from utils import get_row_boundaries, AnalysisConfig, load_and_preprocess_image, get_header_positions
from tools.extract_playerData import *

class RecordDigitDetector:
    """Detects record digits and separator using record-specific templates."""
    
    def __init__(self, templates_dir="assets/templates/digits"):
        self.templates_dir = templates_dir
        self.digit_templates = {}  # Will store record digit templates (0-9)
        self.separator_template = None  # Will store separator template (-)
        
        # Load existing record digit templates
        self._load_record_digit_templates()
    
    def _load_record_digit_templates(self):
        """Load existing record digit templates from disk."""
        # Find all record digit template files
        template_files = glob.glob(os.path.join(self.templates_dir, "record_digit_*.png"))
        
        for template_file in template_files:
            filename = os.path.basename(template_file)
            
            # Parse filename to extract digit value or separator
            import re
            digit_match = re.match(r'record_digit_(\d)\.png', filename)
            separator_match = re.match(r'record_digit_separator\.png', filename)
            
            if digit_match:
                digit_value = int(digit_match.group(1))
                
                # Load template
                template = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    # Convert to binary and store
                    self.digit_templates[digit_value] = self._convert_to_binary(template)
            
            elif separator_match:
                # Load separator template
                template = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    self.separator_template = self._convert_to_binary(template)
    
    def _convert_to_binary(self, image):
        """Convert image to binary for consistent template matching."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return binary
    
    def find_digits_and_separator_by_sliding(self, record_region, confidence_threshold=0.98):
        """Find all record digits and separator in a region using sliding window detection."""
        if record_region.size == 0:
            return []
        
        record_region_binary = self._convert_to_binary(record_region)
        matches = []
        
        # Find digits (0-9)
        for digit_value, template in self.digit_templates.items():
            # Get template dimensions
            template_height, template_width = template.shape
            
            # Skip if template is larger than the region
            if template_height > record_region_binary.shape[0] or template_width > record_region_binary.shape[1]:
                continue
            
            # Slide the template horizontally across the region
            for x in range(record_region_binary.shape[1] - template_width + 1):
                # Extract sub-region at position x
                sub_region = record_region_binary[:template_height, x:x+template_width]
                
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
                        'type': 'digit',
                        'value': digit_value,
                        'x_position': x,
                        'confidence': max_val,
                        'width': template_width
                    })
        
        # Find separator (-)
        if self.separator_template is not None:
            template = self.separator_template
            template_height, template_width = template.shape
            
            # Skip if template is larger than the region
            if template_height <= record_region_binary.shape[0] and template_width <= record_region_binary.shape[1]:
                # Slide the template horizontally across the region
                for x in range(record_region_binary.shape[1] - template_width + 1):
                    # Extract sub-region at position x
                    sub_region = record_region_binary[:template_height, x:x+template_width]
                    
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
                            'type': 'separator',
                            'value': '-',
                            'x_position': x,
                            'confidence': max_val,
                            'width': template_width
                        })
        
        return matches
    
    def reconstruct_record_from_matches(self, matches):
        """Reconstruct a record (wins-losses) from positioned digit and separator matches."""
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
        
        # Find separator position
        separator_pos = None
        for i, match in enumerate(filtered_matches):
            if match['type'] == 'separator':
                separator_pos = i
                break
        
        if separator_pos is None:
            return None  # No separator found
        
        # Split into wins (before separator) and losses (after separator)
        wins_matches = filtered_matches[:separator_pos]
        losses_matches = filtered_matches[separator_pos + 1:]
        
        # Reconstruct wins number
        wins_str = ''.join(str(match['value']) for match in wins_matches if match['type'] == 'digit')
        losses_str = ''.join(str(match['value']) for match in losses_matches if match['type'] == 'digit')
        
        try:
            wins = int(wins_str) if wins_str else 0
            losses = int(losses_str) if losses_str else 0
            
            avg_confidence = sum(match['confidence'] for match in filtered_matches) / len(filtered_matches)
            
            return {
                'wins': wins,
                'losses': losses,
                'confidence': avg_confidence,
                'total_matches': len(filtered_matches)
            }
        except ValueError:
            return None

class RecordExtractor:
    """Extracts record values from scoreboard rows."""
    
    def __init__(self, debug=False):
        self.record_detector = RecordDigitDetector()
        self.debug = debug
    
    def extract_record_region(self, image, row_y, record_column_x):
        """Extract the record region from a specific row."""
        record_width = 100  # Width of record display area
        record_height = 80  # Full row height
        
        # Calculate record region coordinates
        record_y_start = row_y
        record_y_end = record_y_start + record_height
        record_x_start = record_column_x
        record_x_end = record_x_start + record_width
        
        # Extract record region
        record_region = image[record_y_start:record_y_end, record_x_start:record_x_end]
        
        return record_region
    
    def extract_record_value(self, image, row_y, record_column_x):
        """Extract record value using sliding digit detection."""
        record_region = self.extract_record_region(image, row_y, record_column_x)
        
        if record_region.size == 0:
            return {"wins": 0, "losses": 0}
        
        # Try sliding digit detection
        if self.debug:
            print(f"Record templates loaded: {len(self.record_detector.digit_templates)} digits, separator: {self.record_detector.separator_template is not None}")
            if self.record_detector.digit_templates:
                print(f"Available record digits: {list(self.record_detector.digit_templates.keys())}")
        
        # Find all digit and separator matches using sliding window
        matches = self.record_detector.find_digits_and_separator_by_sliding(record_region)
        
        if matches:
            # Reconstruct record from matches
            record_result = self.record_detector.reconstruct_record_from_matches(matches)
            
            if record_result:
                if self.debug:
                    print(f"Found record by sliding digits: {record_result['wins']}-{record_result['losses']} (confidence: {record_result['confidence']:.3f}, matches: {record_result['total_matches']})")
                return {"wins": record_result['wins'], "losses": record_result['losses']}
        
        # Fallback to OCR if needed
        try:
            import pytesseract
            record_region_processed = self._preprocess_for_ocr(record_region)
            record_text = pytesseract.image_to_string(record_region_processed, config='--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789-').strip()
            record = self._parse_record(record_text)
            
            if self.debug:
                print(f"Extracted record by OCR: {record['wins']}-{record['losses']} from text: '{record_text}'")
            
            return record
            
        except Exception as e:
            if self.debug:
                print(f"Record OCR error: {e}")
            return {"wins": 0, "losses": 0}
    
    def _preprocess_for_ocr(self, region):
        """Preprocess image region for better OCR results."""
        # Apply threshold for binary image
        _, binary = cv2.threshold(region, 127, 255, cv2.THRESH_BINARY)
        
        # Scale up for better OCR
        scaled = cv2.resize(binary, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        return scaled
    
    def _parse_record(self, text):
        """Parse record from OCR text."""
        import re
        
        # Look for record patterns like "5-3", "10-2", etc.
        record = {"wins": 0, "losses": 0}
        
        # Try to find X-Y pattern
        record_match = re.search(r'(\d+)-(\d+)', text)
        if record_match:
            wins = int(record_match.group(1))
            losses = int(record_match.group(2))
            
            # Validate reasonable ranges
            if wins <= 20 and losses <= 20:  # Reasonable game limits
                record = {"wins": wins, "losses": losses}
        
        return record

def extract_record_from_scoreboard(image, record_column_x, config):
    """Extract record data for all rows in the scoreboard."""
    # Check if record column was detected
    if record_column_x is None:
        if config.debug:
            print("Record column not detected, returning empty data")
        return []
    
    extractor = RecordExtractor(debug=config.debug)
    record_data = []
    
    # Get row boundaries
    row_boundaries = get_row_boundaries()
    
    for row_num, row_y in enumerate(row_boundaries):
        if config.debug:
            print(f"\n--- Extracting Record for Row {row_num} ---")
        
        record_value = extractor.extract_record_value(image, row_y, record_column_x)
        
        record_data.append({
            "row": row_num,
            "wins": record_value["wins"],
            "losses": record_value["losses"]
        })
        
        if config.debug:
            print(f"Row {row_num}: Record = {record_value['wins']}-{record_value['losses']}")
    
    return record_data

if __name__ == "__main__":
    # Test the record extraction system
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_14.png"
    
    # Load and get header positions
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is not None:
        header_positions = get_header_positions(thresh)
        record_column_x = header_positions.get("RECORD")
        
        if record_column_x:
            print(f"Record column found at x={record_column_x}")
            
            record_data = extract_record_from_scoreboard(image, record_column_x, config)
            
            print(f"\n=== EXTRACTED RECORD DATA ===")
            for row_data in record_data:
                print(f"Row {row_data['row']}: Record = {row_data['wins']}-{row_data['losses']}")
        else:
            print("RECORD column not found in header positions")
    else:
        print(f"Failed to load image: {image_path}") 