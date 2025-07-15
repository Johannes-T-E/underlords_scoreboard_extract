import cv2
import sys
import os

# Handle imports for both standalone and module execution
try:
    from utils import get_row_boundaries
except ImportError:
    # If running from components folder, add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils import AnalysisConfig, get_row_boundaries, load_and_preprocess_image, get_header_positions
from components.hero_extraction import calculate_crew_slots, calculate_bench_slots
from components.image_processing import create_all_slots_masks, load_template_masks, analyze_all_masks

def detect_star_level(thresh, x_center, y_bottom, slot_width=56, star_area_height=18):
    """Detect star level by counting white pixels in the star area below hero icon."""
    # Calculate star area coordinates
    x_start = x_center - slot_width // 2
    x_end = x_start + slot_width
    y_start = y_bottom
    y_end = y_start + star_area_height
    
    # Extract star area from binary image
    star_area = thresh[y_start:y_end, x_start:x_end]
    
    # Count white pixels (value 255 in binary image)
    white_pixel_count = cv2.countNonZero(star_area)
    total_pixels = star_area.shape[0] * star_area.shape[1]
    
    # Calculate white pixel percentage
    white_percentage = (white_pixel_count / total_pixels) * 100 if total_pixels > 0 else 0
    
    # Determine star level based on white pixel percentage
    # These thresholds may need adjustment based on your specific images
    if white_percentage >= 40:
        return 3  # 3 stars
    elif white_percentage >= 20:
        return 2  # 2 stars
    elif white_percentage >= 1:
        return 1  # 1 star
    else:
        return 0  # No stars (empty slot)

def add_star_levels_to_results(thresh, crew_results, bench_results, crew_slots_by_row, bench_slots_by_row, debug=False):
    """Add star level information to hero analysis results."""
    
    # Process crew slots
    for row_num, crew_slots in crew_slots_by_row.items():
        if row_num in crew_results:
            for i, slot in enumerate(crew_slots):
                if i < len(crew_results[row_num]):
                    star_level = detect_star_level(thresh, slot['x_center'], slot['y_end'])
                    crew_results[row_num][i]['star_level'] = star_level
                    
                    if debug:
                        hero_name = crew_results[row_num][i].get('hero_name', 'Unknown')
                        print(f"Row {row_num}, Crew slot {i}: {hero_name} - {star_level} stars")
    
    # Process bench slots
    for row_num, bench_slots in bench_slots_by_row.items():
        if row_num in bench_results:
            for i, slot in enumerate(bench_slots):
                if i < len(bench_results[row_num]):
                    star_level = detect_star_level(thresh, slot['x_center'], slot['y_end'])
                    bench_results[row_num][i]['star_level'] = star_level
                    
                    if debug:
                        hero_name = bench_results[row_num][i].get('hero_name', 'Unknown')
                        print(f"Row {row_num}, Bench slot {i}: {hero_name} - {star_level} stars")
    
    return crew_results, bench_results

def is_filled_slot(slot):
    """Check if a slot contains a valid hero."""
    if not slot:
        return False
    
    hero_name = slot.get('hero_name', '')
    confidence = slot.get('confidence', 0)
    
    # Filter out empty indicators
    if not hero_name or hero_name in ['Unknown', 'Empty', 'None', '']:
        return False
    
    # Filter out very low confidence matches (likely empty slots)
    if confidence < 0.5:
        return False
    
    return True

def extract_crew_and_bench_from_scoreboard(image, thresh, header_positions, config):
    """Extract crew and bench data (heroes and star levels) from scoreboard."""
    # Get header positions for crew and bench
    crew_start_x = header_positions.get("CREW")
    crew_end_x = header_positions.get("UNDERLORD")
    bench_start_x = header_positions.get("BENCH")

    if not crew_start_x and not bench_start_x:
        if config.debug:
            print("Neither crew nor bench columns detected, returning empty data" + "source: crew_bench_extraction.py" + " line 92")
        return {}, {}

    if config.debug:
        print("\n=== EXTRACTING CREW AND BENCH DATA ===" + "source: crew_bench_extraction.py" + " line 96")
        print("Calculating slot positions...")

    # Step 1: Calculate slot positions
    row_boundaries = get_row_boundaries()
    crew_slots_by_row = {}
    bench_slots_by_row = {}

    for row_num, row_boundary in enumerate(row_boundaries):
        if crew_start_x is not None and crew_end_x is not None:
            crew_slots = calculate_crew_slots(crew_start_x, crew_end_x, row_boundary)
            crew_slots_by_row[row_num] = crew_slots
        if bench_start_x is not None:
            bench_slots = calculate_bench_slots(bench_start_x, image.shape[1], row_boundary)
            bench_slots_by_row[row_num] = bench_slots

    if config.debug:
        print(f"Crew slots by row: {[(row, len(slots)) for row, slots in crew_slots_by_row.items()]}")
        print(f"Bench slots by row: {[(row, len(slots)) for row, slots in bench_slots_by_row.items()]}")

    # Step 2: Create slot masks
    if config.debug:
        print("Creating slot masks...")

    crew_masks_by_row, bench_masks_by_row = create_all_slots_masks(image, crew_slots_by_row, bench_slots_by_row)

    if config.debug:
        for row_num in crew_masks_by_row:
            crew_masks = crew_masks_by_row[row_num]
            print(f"Row {row_num}: {len(crew_masks)} crew masks created")
        for row_num in bench_masks_by_row:
            bench_masks = bench_masks_by_row[row_num]
            print(f"Row {row_num}: {len(bench_masks)} bench masks created")

    # Step 3: Analyze heroes
    if config.debug:
        print("Loading template masks...")

    template_masks = load_template_masks("assets/templates/hero_templates/masks", debug=config.debug)

    if config.debug:
        print("Analyzing masks for hero identification...")

    # Only analyze if slots exist
    crew_results, bench_results = {}, {}
    if crew_slots_by_row:
        crew_results, _ = analyze_all_masks(crew_masks_by_row, {}, template_masks, debug=config.debug)
    if bench_slots_by_row:
        _, bench_results = analyze_all_masks({}, bench_masks_by_row, template_masks, debug=config.debug)

    # Step 4: Add star level detection
    if config.debug:
        print("Detecting star levels...")
    crew_results, bench_results = add_star_levels_to_results(thresh, crew_results, bench_results, crew_slots_by_row, bench_slots_by_row, debug=config.debug)

    # Step 5: Filter out empty slots
    for row_num in crew_results:
        crew_results[row_num] = [slot for slot in crew_results[row_num] if is_filled_slot(slot)]
    for row_num in bench_results:
        bench_results[row_num] = [slot for slot in bench_results[row_num] if is_filled_slot(slot)]

    if config.debug:
        total_crew = sum(len(slots) for slots in crew_results.values())
        total_bench = sum(len(slots) for slots in bench_results.values())
        print(f"Final results: {total_crew} crew units, {total_bench} bench units")
        print("##################"+"crew_bench_extraction.py" + " FINISHED ##################")

    return crew_results, bench_results

if __name__ == "__main__":
    # Test the crew and bench extraction system

    
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_04.png"
    
    # Load and preprocess image
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is None:
        print("Failed to load image")
        exit()
    
    # Get header positions
    header_positions = get_header_positions(thresh)
    
    # Extract crew and bench data
    crew_results, bench_results = extract_crew_and_bench_from_scoreboard(image, thresh, header_positions, config)
    
    # Print results
    print("\n=== CREW AND BENCH EXTRACTION RESULTS ===")
    for row_num in crew_results:
        for i, unit in enumerate(crew_results[row_num]):
            print(f"Crew Row {row_num}, Slot {i}: {unit.get('hero_name', 'Unknown')} - {unit.get('star_level', 0)} stars")
    
    for row_num in bench_results:
        for i, unit in enumerate(bench_results[row_num]):
            print(f"Bench Row {row_num}, Slot {i}: {unit.get('hero_name', 'Unknown')} - {unit.get('star_level', 0)} stars") 