import cv2
import numpy as np
from components.utils import load_and_preprocess_image, AnalysisConfig, get_header_positions
from main import calculate_slots

def debug_star_detection():
    """Debug star detection by visualizing star areas."""
    
    # Load image
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_19.png"
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is None:
        print("Failed to load image")
        return
    
    # Get header positions
    header_positions = get_header_positions(thresh)
    crew_start_x = header_positions.get("CREW")
    crew_end_x = header_positions.get("UNDERLORD")
    bench_start_x = header_positions.get("BENCH")
    
    if not crew_start_x or not bench_start_x:
        print("Could not find crew or bench columns")
        return
    
    # Calculate slot positions
    crew_slots_by_row, bench_slots_by_row = calculate_slots(crew_start_x, crew_end_x, bench_start_x, image.shape[1], config)
    
    # Create visualization image
    debug_image = image.copy()
    
    # Debug first few rows only
    for row_num in range(min(3, len(crew_slots_by_row))):
        slots = crew_slots_by_row[row_num]
        
        print(f"\n=== ROW {row_num} CREW SLOTS ===")
        
        # Debug first few slots only
        for i in range(min(5, len(slots))):
            slot = slots[i]
            x_center = slot['x_center']
            y_bottom = slot['y_end']
            
            # Star detection area (same logic as main function)
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
            
            # Debug: Check the actual pixel values in the star area
            if row_num == 0 and i == 0:  # Just for the first slot
                print(f"  Star area shape: {star_area.shape}")
                print(f"  Star area pixel range: {star_area.min()} to {star_area.max()}")
                print(f"  Binary image type: {thresh.dtype}")
                print(f"  Sample star area pixels: {star_area.flatten()[:10]}")
            
            # Save individual star area for debugging
            cv2.imwrite(f"debug_star_area_crew_r{row_num}_s{i}.png", star_area)
            
            # Determine star level
            if white_percentage >= 40:
                star_level = 3
            elif white_percentage >= 20:
                star_level = 2
            elif white_percentage >= 1:
                star_level = 1
            else:
                star_level = 0
            
            print(f"Slot {i}: center=({x_center}, {y_bottom}), star_area=({x_start}, {y_start}, {x_end}, {y_end})")
            print(f"  White pixels: {white_pixel_count}/{total_pixels} ({white_percentage:.1f}%) -> {star_level} stars")
            
            # Draw rectangles on debug image
            # Hero slot area (blue)
            cv2.rectangle(debug_image, (slot['x_start'], slot['y_start']), (slot['x_end'], slot['y_end']), (255, 0, 0), 1)
            # Star detection area (red)
            cv2.rectangle(debug_image, (x_start, y_start), (x_end, y_end), (0, 0, 255), 1)
            
            # Add text labels
            cv2.putText(debug_image, f"C{i}", (slot['x_start'], slot['y_start']-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(debug_image, f"{star_level}*", (x_start, y_end+15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    
    # Also debug bench slots
    for row_num in range(min(3, len(bench_slots_by_row))):
        slots = bench_slots_by_row[row_num]
        
        print(f"\n=== ROW {row_num} BENCH SLOTS ===")
        
        # Debug all bench slots (usually only 3)
        for i in range(len(slots)):
            slot = slots[i]
            x_center = slot['x_center']
            y_bottom = slot['y_end']
            
            # Star detection area (same logic as main function)
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
            
            # Debug: Check the actual pixel values in the star area for bench
            if row_num == 1 and i == 2:  # Just for the bench slot that showed 2 stars
                print(f"  BENCH Star area shape: {star_area.shape}")
                print(f"  BENCH Star area pixel range: {star_area.min()} to {star_area.max()}")
                print(f"  BENCH Sample star area pixels: {star_area.flatten()[:10]}")
            
            # Save individual star area for debugging
            cv2.imwrite(f"debug_star_area_bench_r{row_num}_s{i}.png", star_area)
            
            # Determine star level
            if white_percentage >= 40:
                star_level = 3
            elif white_percentage >= 20:
                star_level = 2
            elif white_percentage >= 1:
                star_level = 1
            else:
                star_level = 0
            
            print(f"Slot {i}: center=({x_center}, {y_bottom}), star_area=({x_start}, {y_start}, {x_end}, {y_end})")
            print(f"  White pixels: {white_pixel_count}/{total_pixels} ({white_percentage:.1f}%) -> {star_level} stars")
            
            # Draw rectangles on debug image
            # Hero slot area (green)
            cv2.rectangle(debug_image, (slot['x_start'], slot['y_start']), (slot['x_end'], slot['y_end']), (0, 255, 0), 2)
            # Star detection area (red)
            cv2.rectangle(debug_image, (x_start, y_start), (x_end, y_end), (0, 0, 255), 2)
            
            # Add text labels
            cv2.putText(debug_image, f"B{i}", (slot['x_start'], slot['y_start']-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(debug_image, f"{star_level}*", (x_start, y_end+15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    
    # Save debug images instead of showing them
    cv2.imwrite("debug_star_detection.png", debug_image)
    cv2.imwrite("debug_thresholded.png", thresh)
    
    print("\nDebug images saved:")
    print("- debug_star_detection.png (with rectangles)")
    print("- debug_thresholded.png (binary image)")

if __name__ == "__main__":
    debug_star_detection() 