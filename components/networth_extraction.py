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


class NetWorthDigitDetector:
    """Detects net worth digits using networth-specific templates."""
    
    def __init__(self, templates_dir="assets/templates/digits"):
        self.templates_dir = templates_dir
        self.digit_templates = {}  # Will store networth digit templates (0-9)
        
        # Load existing networth digit templates
        self._load_networth_digit_templates()
    
    def _load_networth_digit_templates(self):
        """Load existing networth digit templates from disk."""
        # Find all networth digit template files
        template_files = glob.glob(os.path.join(self.templates_dir, "NetWorth_digit_*.png"))
        
        for template_file in template_files:
            filename = os.path.basename(template_file)
            
            # Parse filename to extract digit value: NetWorth_digit_5.png
            import re
            match = re.match(r'NetWorth_digit_(\d)\.png', filename)
            
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
    
    def find_digits_by_sliding(self, networth_region, confidence_threshold=0.95):
        """Find all networth digits in a region using sliding window detection."""
        if networth_region.size == 0:
            return []
        
        networth_region_binary = self._convert_to_binary(networth_region)
        matches = []
        
        # For each digit (0-9)
        for digit_value, template in self.digit_templates.items():
            # Get template dimensions
            template_height, template_width = template.shape
            
            # Skip if template is larger than the region
            if template_height > networth_region_binary.shape[0] or template_width > networth_region_binary.shape[1]:
                continue
            
            # Slide the template horizontally across the region
            for x in range(networth_region_binary.shape[1] - template_width + 1):
                # Extract sub-region at position x
                sub_region = networth_region_binary[:template_height, x:x+template_width]
                
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
        """Reconstruct a networth number from positioned digit matches."""
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

class NetWorthExtractor:
    """Extracts net worth values from scoreboard rows."""
    
    def __init__(self, debug=False):
        self.debug = debug
    
    def extract_networth_region(self, image, row_y, networth_column_x):
        """Extract the networth region from a specific row."""
        networth_width = 100  # Width of networth display area
        networth_height = 80  # Full row height
        
        # Calculate networth region coordinates
        networth_y_start = row_y
        networth_y_end = networth_y_start + networth_height
        networth_x_start = networth_column_x
        networth_x_end = networth_x_start + networth_width
        
        # Extract networth region
        networth_region = image[networth_y_start:networth_y_end, networth_x_start:networth_x_end]
        
        return networth_region
    
    def extract_networth_value(self, image, row_y, networth_column_x):
        """Extract networth value using sliding digit detection."""
        networth_region = self.extract_networth_region(image, row_y, networth_column_x)
        
        if networth_region.size == 0:
            return 0
        
        # Try sliding digit detection using shared detector
        # Find all digit matches using sliding window
        digit_matches = shared_detector.find_digits_by_sliding(networth_region, 'networth')
        
        if digit_matches:
            # Reconstruct number from digit matches
            number_result = shared_detector.reconstruct_number_from_matches(digit_matches)
            
            if number_result and number_result['number'] >= 0 and number_result['number'] <= 1000:
                if self.debug:
                    print(f"Found networth by sliding digits: {number_result['number']} (confidence: {number_result['confidence']:.3f}, digits: {number_result['digit_count']})")
                return number_result['number']
        
        # Fallback to OCR if needed
        try:
            import pytesseract
            networth_region_processed = self._preprocess_for_ocr(networth_region)
            networth_text = pytesseract.image_to_string(networth_region_processed, config='--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789').strip()
            networth = self._parse_networth(networth_text)
            
            if self.debug:
                print(f"Extracted networth by OCR: {networth} from text: '{networth_text}'")
            
            return networth
            
        except Exception as e:
            if self.debug:
                print(f"NetWorth OCR error: {e}")
            return 0
    
    def _preprocess_for_ocr(self, region):
        """Preprocess image region for better OCR results."""
        # Apply threshold for binary image
        _, binary = cv2.threshold(region, 127, 255, cv2.THRESH_BINARY)
        
        # Scale up for better OCR
        scaled = cv2.resize(binary, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        return scaled
    
    def _parse_networth(self, text):
        """Parse networth from OCR text."""
        import re
        
        # Look for networth patterns
        networth = 0
        
        networth_matches = re.findall(r'(\d+)', text)
        for match in networth_matches:
            potential_networth = int(match)
            if potential_networth >= 0 and potential_networth <= 1000:  # Valid networth range
                networth = potential_networth
                break
        
        return networth

def extract_networth_from_scoreboard(image, networth_column_x, config):
    """Extract networth data for all rows in the scoreboard."""
    if config.debug:
        print(f"###########################################################################################"+" networth_extraction.py" + " - STARTED ")
        # Show template loading status once
        networth_templates = shared_detector.get_digit_templates('networth')
        print(f"NetWorth templates loaded: {len(networth_templates)} templates")
        if networth_templates:
            print(f"Available networth digits: {list(networth_templates.keys())}")
    
    # Check if networth column was detected
    if networth_column_x is None:
        if config.debug:
            print("NetWorth column not detected, returning empty data")
        return []
    
    extractor = NetWorthExtractor(debug=config.debug)
    networth_data = []
    
    # Get row boundaries
    row_boundaries = get_row_boundaries()
    
    for row_num, row_y in enumerate(row_boundaries):
        if config.debug:
            print(f"\n--- Extracting NetWorth for Row {row_num} ---")
        
        networth_value = extractor.extract_networth_value(image, row_y, networth_column_x)
        
        networth_data.append({
            "row": row_num,
            "networth": networth_value
        })
        
        if config.debug:
            print(f"Row {row_num}: NetWorth = {networth_value}")
    if config.debug:
        print(f"###########################################################################################"+" networth_extraction.py" + " - FINISHED")
    return networth_data

if __name__ == "__main__":
    # Test the networth extraction system
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_14.png"
    
    # Load and get header positions
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is not None:
        header_positions = get_header_positions(thresh)
        networth_column_x = header_positions.get("NETWORTH")
        
        if networth_column_x:
            print(f"NetWorth column found at x={networth_column_x}")
            
            networth_data = extract_networth_from_scoreboard(image, networth_column_x, config)
            
            print(f"\n=== EXTRACTED NETWORTH DATA ===")
            for row_data in networth_data:
                print(f"Row {row_data['row']}: NetWorth = {row_data['networth']}")
        else:
            print("NETWORTH column not found in header positions")
    else:
        print(f"Failed to load image: {image_path}") 