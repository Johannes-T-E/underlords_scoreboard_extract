import cv2
import numpy as np
from utils import AnalysisConfig, load_and_preprocess_image, get_row_boundaries
from components.player_extraction import PlayerExtractor
import os

def debug_failing_levels():
    """Debug the specific rows that are failing level detection."""
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_18.png"
    
    # Load image
    image, thresh = load_and_preprocess_image(image_path, config)
    if image is None:
        print("Failed to load image")
        return
    
    # Get row boundaries  
    row_boundaries = get_row_boundaries()
    extractor = PlayerExtractor(debug=True)
    
    # Focus on the failing rows (1 and 7)
    failing_rows = [1, 7]
    
    print("=== DEBUG FAILING LEVEL DETECTION ===\n")
    
    for row_num in failing_rows:
        print(f"\n--- Debugging Row {row_num} ---")
        
        row_y = row_boundaries[row_num]
        
        # Extract name first
        name_result = extractor.extract_player_name(image, row_y)
        player_name = name_result["player_name"]
        print(f"Player: {player_name}")
        
        # Extract level region
        info_y_start = row_y + 39  # PLAYER_INFO_Y_START
        info_y_end = info_y_start + 20  # PLAYER_INFO_HEIGHT
        info_x_start = 120  # PLAYER_INFO_X_START
        
        # Test wider region (30px)
        level_region = image[info_y_start:info_y_end, info_x_start:info_x_start + 30]
        
        print(f"Level region shape: {level_region.shape}")
        
        # Save for visual inspection
        os.makedirs("debug_failing", exist_ok=True)
        cv2.imwrite(f"debug_failing/row_{row_num}_level_region.png", level_region)
        
        # Convert to binary to see what the templates are matching against
        binary_region = extractor.digit_detector._convert_to_binary(level_region)
        cv2.imwrite(f"debug_failing/row_{row_num}_level_binary.png", binary_region)
        
        print(f"Binary region shape: {binary_region.shape}")
        
        # Check what digits are available
        print(f"Available digit templates: {list(extractor.digit_detector.digit_templates.keys())}")
        
        # Test digit detection manually
        digit_matches = extractor.digit_detector.find_digits_by_sliding(level_region)
        print(f"Found {len(digit_matches)} digit matches:")
        
        for match in digit_matches:
            print(f"  Digit {match['digit']}: x={match['x_position']}, confidence={match['confidence']:.3f}, width={match['width']}")
        
        # Test reconstruction
        result = extractor.digit_detector.reconstruct_number_from_matches(digit_matches)
        print(f"Reconstruction result: {result}")
        
        # Let's manually check if this could be a "10" by looking for "1" and "0"
        print("\n--- Manual check for digits 1 and 0 ---")
        
        # Check for digit "1" specifically
        if 1 in extractor.digit_detector.digit_templates:
            template_1 = extractor.digit_detector.digit_templates[1]
            result_1 = cv2.matchTemplate(binary_region, template_1, cv2.TM_CCOEFF_NORMED)
            _, max_val_1, _, max_loc_1 = cv2.minMaxLoc(result_1)
            print(f"Digit 1 template match: confidence={max_val_1:.3f} at position {max_loc_1}")
        
        # Check for digit "0" specifically
        if 0 in extractor.digit_detector.digit_templates:
            template_0 = extractor.digit_detector.digit_templates[0]
            result_0 = cv2.matchTemplate(binary_region, template_0, cv2.TM_CCOEFF_NORMED)
            _, max_val_0, _, max_loc_0 = cv2.minMaxLoc(result_0)
            print(f"Digit 0 template match: confidence={max_val_0:.3f} at position {max_loc_0}")
        
        # Test if the problem is with confidence threshold
        print(f"\n--- Testing with lower confidence threshold ---")
        digit_matches_low = extractor.digit_detector.find_digits_by_sliding(level_region, confidence_threshold=0.7)
        print(f"Found {len(digit_matches_low)} digit matches with 0.7 threshold:")
        
        for match in digit_matches_low:
            print(f"  Digit {match['digit']}: x={match['x_position']}, confidence={match['confidence']:.3f}, width={match['width']}")
        
        result_low = extractor.digit_detector.reconstruct_number_from_matches(digit_matches_low)
        print(f"Reconstruction result with lower threshold: {result_low}")
        
        print("-" * 80)

if __name__ == "__main__":
    debug_failing_levels() 