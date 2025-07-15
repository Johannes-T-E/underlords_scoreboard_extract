import cv2
import numpy as np
import os
import glob
import sys

# Handle imports for both standalone and module execution
try:
    from utils import get_row_boundaries, AnalysisConfig, load_and_preprocess_image, get_header_positions
    from components.shared_digit_detector import shared_detector
except ImportError:
    # If running from components folder, add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils import get_row_boundaries, AnalysisConfig, load_and_preprocess_image, get_header_positions
    from components.shared_digit_detector import shared_detector

class HealthDigitDetector:
    """Detects health digits using health-specific templates."""
    
    def __init__(self, templates_dir="assets/templates/digits"):
        self.templates_dir = templates_dir
        self.digit_templates = {}  # Will store health digit templates (0-9)
        
        # Load existing health digit templates
        self._load_health_digit_templates()
    
    def _load_health_digit_templates(self):
        """Load existing health digit templates from disk."""
        # Find all health digit template files
        template_files = glob.glob(os.path.join(self.templates_dir, "health_digit_*.png"))
        
        for template_file in template_files:
            filename = os.path.basename(template_file)
            
            # Parse filename to extract digit value: health_digit_5.png
            import re
            match = re.match(r'health_digit_(\d)\.png', filename)
            
            if match:
                digit_value = int(match.group(1))
                
                # Load template
                template = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    # Convert to binary and store
                    self.digit_templates[digit_value] = self._convert_to_binary(template)
    
    def _convert_to_binary(self, image):
        """Convert image to binary for consistent template matching."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return binary
    
    def find_digits_by_sliding(self, health_region, confidence_threshold=0.98):
        """Find all health digits in a region using sliding window detection."""
        if health_region.size == 0:
            return []
        
        health_region_binary = self._convert_to_binary(health_region)
        matches = []
        
        # For each digit (0-9)
        for digit_value, template in self.digit_templates.items():
            # Get template dimensions
            template_height, template_width = template.shape
            
            # Skip if template is larger than the region
            if template_height > health_region_binary.shape[0] or template_width > health_region_binary.shape[1]:
                continue
            
            # Slide the template horizontally across the region
            for x in range(health_region_binary.shape[1] - template_width + 1):
                # Extract sub-region at position x
                sub_region = health_region_binary[:template_height, x:x+template_width]
                
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
        """Reconstruct a health number from positioned digit matches."""
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

class HealthExtractor:
    """Extracts health values from scoreboard rows."""
    
    def __init__(self, debug=False):
        self.debug = debug
    
    def extract_health_region(self, image, row_y, health_column_x):
        """Extract the health region from a specific row."""
        health_width = 100  # Width of health display area
        health_height = 80  # Full row height
        
        # Calculate health region coordinates
        health_y_start = row_y
        health_y_end = health_y_start + health_height
        health_x_start = health_column_x
        health_x_end = health_x_start + health_width
        
        # Extract health region
        health_region = image[health_y_start:health_y_end, health_x_start:health_x_end]
        
        return health_region
    
    def extract_health_value(self, image, row_y, health_column_x):
        """Extract health value using sliding digit detection."""
        health_region = self.extract_health_region(image, row_y, health_column_x)
        
        if health_region.size == 0:
            return 0
        
        # Try sliding digit detection using shared detector
        # Find all digit matches using sliding window
        digit_matches = shared_detector.find_digits_by_sliding(health_region, 'health')
        
        if digit_matches:
            # Reconstruct number from digit matches
            number_result = shared_detector.reconstruct_number_from_matches(digit_matches)
            
            if number_result and number_result['number'] >= 0 and number_result['number'] <= 100:
                if self.debug:
                    print(f"Found health by sliding digits: {number_result['number']} (confidence: {number_result['confidence']:.3f}, digits: {number_result['digit_count']})")
                return number_result['number']
        
        # Fallback to OCR if needed
        try:
            import pytesseract
            health_region_processed = self._preprocess_for_ocr(health_region)
            health_text = pytesseract.image_to_string(health_region_processed, config='--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789').strip()
            health = self._parse_health(health_text)
            
            if self.debug:
                print(f"Extracted health by OCR: {health} from text: '{health_text}'")
            
            return health
            
        except Exception as e:
            if self.debug:
                print(f"Health OCR error: {e}")
            return 0
    
    def _preprocess_for_ocr(self, region):
        """Preprocess image region for better OCR results."""
        # Apply threshold for binary image
        _, binary = cv2.threshold(region, 127, 255, cv2.THRESH_BINARY)
        
        # Scale up for better OCR
        scaled = cv2.resize(binary, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        return scaled
    
    def _parse_health(self, text):
        """Parse health from OCR text."""
        import re
        
        # Look for health patterns
        health = 0
        
        health_matches = re.findall(r'(\d+)', text)
        for match in health_matches:
            potential_health = int(match)
            if potential_health >= 0 and potential_health <= 100:  # Valid health range
                health = potential_health
                break
        
        return health

def extract_health_from_scoreboard(image, health_column_x, config):
    """Extract health data for all rows in the scoreboard."""
    if config.debug:
        print(f"###########################################################################################"+" health_extraction.py" + " - STARTED ")
        # Show template loading status once
        health_templates = shared_detector.get_digit_templates('health')
        print(f"Health templates loaded: {len(health_templates)} templates")
        if health_templates:
            print(f"Available health digits: {list(health_templates.keys())}")
    
    # Check if health column was detected
    if health_column_x is None:
        if config.debug:
            print("Health column not detected, returning empty data")
        return []
    
    extractor = HealthExtractor(debug=config.debug)
    health_data = []
    
    # Get row boundaries
    row_boundaries = get_row_boundaries()
    
    for row_num, row_y in enumerate(row_boundaries):
        if config.debug:
            print(f"\n--- Extracting Health for Row {row_num} ---")
        
        health_value = extractor.extract_health_value(image, row_y, health_column_x)
        
        health_data.append({
            "row": row_num,
            "health": health_value
        })
        
        if config.debug:
            print(f"Row {row_num}: Health = {health_value}")
    if config.debug:
        print(f"###########################################################################################"+" health_extraction.py" + " - FINISHED")
    return health_data

if __name__ == "__main__":
    # Test the health extraction system
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_14.png"
    
    # Load and get header positions
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is not None:
        header_positions = get_header_positions(thresh)
        health_column_x = header_positions.get("HEALTH")
        
        if health_column_x:
            print(f"Health column found at x={health_column_x}")
            
            health_data = extract_health_from_scoreboard(image, health_column_x, config)
            
            print(f"\n=== EXTRACTED HEALTH DATA ===")
            for row_data in health_data:
                print(f"Row {row_data['row']}: Health = {row_data['health']}")
        else:
            print("HEALTH column not found in header positions")
    else:
        print(f"Failed to load image: {image_path}") 