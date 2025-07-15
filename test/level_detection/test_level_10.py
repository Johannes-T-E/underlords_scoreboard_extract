import cv2
import numpy as np
from components.player_extraction import DigitDetector

def test_level_10_detection():
    """Test that the system can detect level 10 (2-digit level)."""
    
    # Initialize digit detector
    detector = DigitDetector()
    
    print("=== TESTING LEVEL 10 DETECTION ===")
    print(f"Available digit templates: {list(detector.digit_templates.keys())}")
    
    # Load digit templates for 1 and 0
    if 1 not in detector.digit_templates or 0 not in detector.digit_templates:
        print("Error: Missing digit templates for 1 or 0")
        return
    
    template_1 = detector.digit_templates[1]
    template_0 = detector.digit_templates[0]
    
    print(f"Template 1 shape: {template_1.shape}")
    print(f"Template 0 shape: {template_0.shape}")
    
    # Create a mock level region with "10" by combining templates
    height = max(template_1.shape[0], template_0.shape[0])
    width = template_1.shape[1] + template_0.shape[1] + 2  # Small gap between digits
    
    # Create a binary image with "10"
    mock_region = np.zeros((height, width), dtype=np.uint8)
    
    # Place "1" at the beginning
    mock_region[:template_1.shape[0], :template_1.shape[1]] = template_1
    
    # Place "0" after the "1" with a small gap
    start_x = template_1.shape[1] + 2
    mock_region[:template_0.shape[0], start_x:start_x + template_0.shape[1]] = template_0
    
    # Save the mock region for visual inspection
    cv2.imwrite("debug_level_10_mock.png", mock_region)
    print(f"Mock region shape: {mock_region.shape}")
    
    # Test digit detection on the mock region
    print("\n--- Testing digit detection on mock level 10 ---")
    
    # Test with default confidence threshold (0.95)
    digit_matches = detector.find_digits_by_sliding(mock_region)
    print(f"Found {len(digit_matches)} digit matches:")
    
    for match in digit_matches:
        print(f"  Digit {match['digit']}: x={match['x_position']}, confidence={match['confidence']:.3f}, width={match['width']}")
    
    # Test reconstruction
    result = detector.reconstruct_number_from_matches(digit_matches)
    print(f"Reconstruction result: {result}")
    
    if result and result['number'] == 10:
        print("✅ SUCCESS: Level 10 detection works!")
        return True
    else:
        print("❌ FAILED: Level 10 detection not working")
        
        # Try with lower confidence threshold
        print("\n--- Testing with lower confidence threshold (0.85) ---")
        digit_matches_low = detector.find_digits_by_sliding(mock_region, confidence_threshold=0.85)
        print(f"Found {len(digit_matches_low)} digit matches:")
        
        for match in digit_matches_low:
            print(f"  Digit {match['digit']}: x={match['x_position']}, confidence={match['confidence']:.3f}, width={match['width']}")
        
        result_low = detector.reconstruct_number_from_matches(digit_matches_low)
        print(f"Reconstruction result: {result_low}")
        
        if result_low and result_low['number'] == 10:
            print("✅ SUCCESS: Level 10 detection works with lower threshold!")
            return True
        else:
            print("❌ FAILED: Level 10 detection still not working")
            return False

if __name__ == "__main__":
    test_level_10_detection() 