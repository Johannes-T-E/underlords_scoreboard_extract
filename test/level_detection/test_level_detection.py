import cv2
import numpy as np
from utils import AnalysisConfig, load_and_preprocess_image, get_row_boundaries
from components.player_extraction import PlayerExtractor
import os

def test_level_detection():
    """Test level detection for all players to identify 2-digit level issues."""
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
    
    print("=== TESTING LEVEL DETECTION ===\n")
    
    for row_num, row_y in enumerate(row_boundaries):
        print(f"\n--- Testing Row {row_num} ---")
        
        # Extract name first
        name_result = extractor.extract_player_name(image, row_y)
        player_name = name_result["player_name"]
        print(f"Player: {player_name}")
        
        # Test different level region sizes
        info_y_start = row_y + 39  # PLAYER_INFO_Y_START
        info_y_end = info_y_start + 20  # PLAYER_INFO_HEIGHT
        info_x_start = 120  # PLAYER_INFO_X_START
        
        # Test current region (15px wide)
        current_region = image[info_y_start:info_y_end, info_x_start:info_x_start + 15]
        
        # Test wider region (30px wide)
        wider_region = image[info_y_start:info_y_end, info_x_start:info_x_start + 30]
        
        # Test even wider region (40px wide)
        widest_region = image[info_y_start:info_y_end, info_x_start:info_x_start + 40]
        
        print(f"Current region (15px): {current_region.shape}")
        print(f"Wider region (30px): {wider_region.shape}")
        print(f"Widest region (40px): {widest_region.shape}")
        
        # Save regions for visual inspection
        os.makedirs("debug_regions", exist_ok=True)
        cv2.imwrite(f"debug_regions/row_{row_num}_level_15px.png", current_region)
        cv2.imwrite(f"debug_regions/row_{row_num}_level_30px.png", wider_region)
        cv2.imwrite(f"debug_regions/row_{row_num}_level_40px.png", widest_region)
        
        # Test digit detection on different regions
        print("\n--- Testing digit detection on different region sizes ---")
        
        # Test current region
        digit_matches_15 = extractor.digit_detector.find_digits_by_sliding(current_region)
        result_15 = extractor.digit_detector.reconstruct_number_from_matches(digit_matches_15)
        print(f"15px region: {result_15}")
        
        # Test wider region
        digit_matches_30 = extractor.digit_detector.find_digits_by_sliding(wider_region)
        result_30 = extractor.digit_detector.reconstruct_number_from_matches(digit_matches_30)
        print(f"30px region: {result_30}")
        
        # Test widest region
        digit_matches_40 = extractor.digit_detector.find_digits_by_sliding(widest_region)
        result_40 = extractor.digit_detector.reconstruct_number_from_matches(digit_matches_40)
        print(f"40px region: {result_40}")
        
        # Show what the current extraction returns
        current_level = extractor.extract_player_level(image, row_y)
        print(f"Current extraction result: {current_level}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_level_detection() 