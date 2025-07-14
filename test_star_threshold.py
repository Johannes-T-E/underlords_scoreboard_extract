import cv2
import numpy as np
from utils import AnalysisConfig, get_header_positions
from main import calculate_slots

def test_star_thresholds():
    """Test different threshold values to find optimal for brown stars."""
    
    # Load image
    image_path = "assets/templates/screenshots_for_templates/SS_19.png"
    image = cv2.imread(image_path)
    if image is None:
        print("Failed to load image")
        return
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Test different thresholds
    thresholds = [90, 100, 110, 120, 127, 140, 150]
    
    print("Testing different thresholds for star detection:")
    print("=" * 60)
    
    for threshold_val in thresholds:
        print(f"\nTesting threshold: {threshold_val}")
        
        # Apply threshold
        _, thresh = cv2.threshold(gray, threshold_val, 255, cv2.THRESH_BINARY)
        
        # Get header positions for slot calculation
        header_positions = get_header_positions(thresh)
        crew_start_x = header_positions.get("CREW")
        crew_end_x = header_positions.get("UNDERLORD")
        bench_start_x = header_positions.get("BENCH")
        
        if not crew_start_x or not bench_start_x:
            print(f"  Could not find columns at threshold {threshold_val}")
            continue
        
        # Calculate slots
        config = AnalysisConfig(debug=False)
        crew_slots_by_row, bench_slots_by_row = calculate_slots(crew_start_x, crew_end_x, bench_start_x, image.shape[1], config)
        
        # Test first few slots
        print(f"  Crew slots (first 3):")
        for i in range(min(3, len(crew_slots_by_row[0]))):
            slot = crew_slots_by_row[0][i]
            x_center = slot['x_center']
            y_bottom = slot['y_end']
            
            # Star detection area
            slot_width = 56
            star_area_height = 18
            x_start = x_center - slot_width // 2
            x_end = x_start + slot_width
            y_start = y_bottom
            y_end = y_start + star_area_height
            
            # Extract star area
            star_area = thresh[y_start:y_end, x_start:x_end]
            white_pixel_count = cv2.countNonZero(star_area)
            total_pixels = star_area.shape[0] * star_area.shape[1]
            white_percentage = (white_pixel_count / total_pixels) * 100 if total_pixels > 0 else 0
            
            # Determine star level
            if white_percentage >= 40:
                star_level = 3
            elif white_percentage >= 20:
                star_level = 2
            elif white_percentage >= 1:
                star_level = 1
            else:
                star_level = 0
            
            print(f"    Slot {i}: {white_percentage:.1f}% white -> {star_level} stars")
        
        # Test first few bench slots
        print(f"  Bench slots (first 3):")
        for i in range(min(3, len(bench_slots_by_row[0]))):
            slot = bench_slots_by_row[0][i]
            x_center = slot['x_center']
            y_bottom = slot['y_end']
            
            # Star detection area
            slot_width = 56
            star_area_height = 18
            x_start = x_center - slot_width // 2
            x_end = x_start + slot_width
            y_start = y_bottom
            y_end = y_start + star_area_height
            
            # Extract star area
            star_area = thresh[y_start:y_end, x_start:x_end]
            white_pixel_count = cv2.countNonZero(star_area)
            total_pixels = star_area.shape[0] * star_area.shape[1]
            white_percentage = (white_pixel_count / total_pixels) * 100 if total_pixels > 0 else 0
            
            # Determine star level
            if white_percentage >= 40:
                star_level = 3
            elif white_percentage >= 20:
                star_level = 2
            elif white_percentage >= 1:
                star_level = 1
            else:
                star_level = 0
            
            print(f"    Slot {i}: {white_percentage:.1f}% white -> {star_level} stars")
        
        # Save debug image for this threshold
        cv2.imwrite(f"debug_threshold_{threshold_val}.png", thresh)
    
    print(f"\nDebug images saved for each threshold value.")
    print("Check debug_threshold_XXX.png files to see which captures brown stars best.")

if __name__ == "__main__":
    test_star_thresholds() 