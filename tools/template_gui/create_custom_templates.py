import cv2
import numpy as np
import os
import json
from pathlib import Path
from datetime import datetime

# Add test modules and components for slot calculation
import sys
sys.path.append('.')
from test_hero_slots import calculate_hero_slots, get_fixed_row_boundaries
from column_detection import find_column_headers_complete

def process_slot_for_template(slot_image, sample_x=3, sample_y=3, tolerance=2, crop_size=28):
    """Process a slot to create a template and mask."""
    if slot_image.shape[0] < crop_size or slot_image.shape[1] < crop_size:
        return None, None
    
    # Crop to top-left region (same as our matching approach)
    slot_crop = slot_image[:crop_size, :crop_size]
    h, w = slot_crop.shape[:2]
    
    # Sample background color
    if sample_y >= h or sample_x >= w:
        sample_x, sample_y = 0, 0
    
    bg_color_bgr = tuple(slot_crop[sample_y, sample_x].astype(int))
    
    # Create color range for background removal
    lower_bound = np.array([max(0, c - tolerance) for c in bg_color_bgr])
    upper_bound = np.array([min(255, c + tolerance) for c in bg_color_bgr])
    
    # Remove background
    processed_template = slot_crop.copy()
    bg_mask = cv2.inRange(slot_crop, lower_bound, upper_bound)
    processed_template[bg_mask > 0] = [255, 255, 255]  # Set background to white
    
    # Create mask: white = 0 (ignore), non-white = 255 (use for matching)
    white_pixels = cv2.inRange(processed_template, np.array([255, 255, 255]), np.array([255, 255, 255]))
    mask = np.where(white_pixels > 0, 0, 255).astype(np.uint8)
    
    return processed_template, mask

def extract_templates_from_screenshot(image_path, hero_mappings, output_dir="custom_templates"):
    """
    Extract hero templates from a screenshot.
    
    Args:
        image_path: Path to screenshot
        hero_mappings: Dict like {"row1crew0": "luna", "row1crew1": "tusk", "row2bench3": "axe"}
        output_dir: Directory to save templates
    """
    print(f"Processing screenshot: {image_path}")
    print(f"Hero mappings: {len(hero_mappings)} heroes specified")
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Failed to load image: {image_path}")
        return False
    
    # Get column headers and calculate slots
    headers, _ = find_column_headers_complete(image)
    if not headers:
        print("No headers found")
        return False
    
    # Get column positions
    crew_start_x = headers.get('CREW', [None])[0] if 'CREW' in headers else None
    crew_end_x = headers.get('UNDERLORD', [None])[0] if 'UNDERLORD' in headers else None
    bench_start_x = headers.get('BENCH', [None])[0] if 'BENCH' in headers else None
    
    if not crew_start_x or not crew_end_x:
        print("Required columns not found")
        return False
    
    # Calculate slots
    crew_slots = calculate_hero_slots(crew_start_x, crew_end_x)
    bench_slots = calculate_hero_slots(bench_start_x, image.shape[1], max_slots=8) if bench_start_x else []
    
    # Get row boundaries  
    row_starts = get_fixed_row_boundaries()
    
    print(f"Found {len(crew_slots)} crew slots, {len(bench_slots)} bench slots")
    
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/templates", exist_ok=True)
    os.makedirs(f"{output_dir}/masks", exist_ok=True)
    os.makedirs(f"{output_dir}/originals", exist_ok=True)
    os.makedirs(f"{output_dir}/debug", exist_ok=True)
    
    extracted_count = 0
    failed_extractions = []
    
    # Process each specified hero mapping
    for slot_id, hero_name in hero_mappings.items():
        print(f"\nExtracting {hero_name} from {slot_id}...")
        
        # Parse slot_id (e.g., "row1crew0", "row2bench3")
        try:
            if slot_id.startswith("row"):
                row_part = slot_id[3:slot_id.find("crew") if "crew" in slot_id else slot_id.find("bench")]
                row_idx = int(row_part) - 1  # Convert to 0-based
                
                if "crew" in slot_id:
                    slot_idx = int(slot_id.split("crew")[1])
                    slot_type = "crew"
                    slots = crew_slots
                elif "bench" in slot_id:
                    slot_idx = int(slot_id.split("bench")[1])
                    slot_type = "bench"
                    slots = bench_slots
                else:
                    print(f"  Invalid slot format: {slot_id}")
                    failed_extractions.append((slot_id, hero_name, "Invalid format"))
                    continue
            else:
                print(f"  Invalid slot format: {slot_id}")
                failed_extractions.append((slot_id, hero_name, "Invalid format"))
                continue
                
        except (ValueError, IndexError) as e:
            print(f"  Failed to parse slot_id: {slot_id} - {e}")
            failed_extractions.append((slot_id, hero_name, f"Parse error: {e}"))
            continue
        
        # Validate indices
        if row_idx >= len(row_starts) - 1:
            print(f"  Row {row_idx + 1} out of range")
            failed_extractions.append((slot_id, hero_name, "Row out of range"))
            continue
            
        if slot_idx >= len(slots):
            print(f"  {slot_type.capitalize()} slot {slot_idx} out of range")
            failed_extractions.append((slot_id, hero_name, "Slot out of range"))
            continue
        
        # Extract slot
        row_start = row_starts[row_idx]
        slot_start, slot_end, slot_center = slots[slot_idx]
        
        # Calculate exact 56x56 slot position with 5px top margin
        slot_top = row_start + 5
        slot_bottom = slot_top + 56
        slot_image = image[slot_top:slot_bottom, slot_start:slot_end]
        
        if slot_image.shape[0] != 56 or slot_image.shape[1] != 56:
            print(f"  Warning: Extracted slot is {slot_image.shape[1]}x{slot_image.shape[0]}, expected 56x56")
        
        if slot_image.size == 0:
            print(f"  Failed to extract slot")
            failed_extractions.append((slot_id, hero_name, "Empty slot"))
            continue
        
        # Process the slot to create template and mask
        template, mask = process_slot_for_template(slot_image)
        if template is None:
            print(f"  Failed to process slot")
            failed_extractions.append((slot_id, hero_name, "Processing failed"))
            continue
        
        # Save files
        template_filename = f"{hero_name}_template.png"
        mask_filename = f"{hero_name}_mask.png"
        original_filename = f"{hero_name}_original_56x56.png"
        crop_filename = f"{hero_name}_crop_28x28.png"
        
        # Save processed template (28x28)
        cv2.imwrite(f"{output_dir}/templates/{template_filename}", template)
        
        # Save mask (28x28)
        cv2.imwrite(f"{output_dir}/masks/{mask_filename}", mask)
        
        # Save original slot (56x56) for reference
        cv2.imwrite(f"{output_dir}/originals/{original_filename}", slot_image)
        
        # Save cropped version (28x28) for comparison
        slot_crop = slot_image[:28, :28]
        cv2.imwrite(f"{output_dir}/debug/{crop_filename}", slot_crop)
        
        # Create debug comparison image
        debug_comparison = np.hstack([
            slot_crop,  # Original crop
            np.zeros((28, 2, 3), dtype=np.uint8),  # separator
            template,   # Processed template
            np.zeros((28, 2, 3), dtype=np.uint8),  # separator
            cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)  # Mask
        ])
        cv2.imwrite(f"{output_dir}/debug/{hero_name}_debug.png", debug_comparison)
        
        # Stats
        hero_pixels = np.sum(mask > 0)
        total_pixels = 28 * 28
        
        print(f"  ✅ Extracted {hero_name}: {hero_pixels}/{total_pixels} hero pixels ({hero_pixels/total_pixels*100:.1f}%)")
        extracted_count += 1
    
    # Save extraction metadata
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "source_image": image_path,
        "hero_mappings": hero_mappings,
        "extracted_count": extracted_count,
        "failed_extractions": failed_extractions,
        "output_directory": output_dir
    }
    
    with open(f"{output_dir}/extraction_log.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Successfully extracted: {extracted_count} heroes")
    print(f"Failed extractions: {len(failed_extractions)}")
    
    if failed_extractions:
        print(f"\nFailed extractions:")
        for slot_id, hero_name, reason in failed_extractions:
            print(f"  {slot_id} ({hero_name}): {reason}")
    
    print(f"\nFiles saved to: {output_dir}/")
    print(f"- templates/: Processed 28x28 templates (background removed)")
    print(f"- masks/: 28x28 masks (255=hero, 0=background)")
    print(f"- originals/: Original 56x56 slot crops")
    print(f"- debug/: Debug comparisons and crops")
    
    return extracted_count > 0

def get_all_underlords_heroes():
    """Get list of all possible heroes."""
    heroes = [
        'abaddon', 'alchemist', 'antimage', 'axe', 'batrider', 'beastmaster', 
        'bounty_hunter', 'bristleback', 'chaos_knight', 'crystal_maiden', 
        'dazzle', 'death_prophet', 'doom_bringer', 'dragon_knight', 'drow_ranger',
        'earth_spirit', 'ember_spirit', 'enchantress', 'faceless_void', 'furion',
        'juggernaut', 'keeper_of_the_light', 'kunkka', 'legion_commander', 'lich',
        'life_stealer', 'lina', 'lone_druid', 'luna', 'lycan', 'magnataur',
        'medusa', 'meepo', 'mirana', 'omniknight', 'pangolier', 'phantom_assassin',
        'puck', 'pudge', 'queenofpain', 'rubick', 'shadow_demon', 'shadow_shaman',
        'skeleton_king', 'slardar', 'slark', 'snapfire', 'spectre', 'spirit_breaker',
        'storm_spirit', 'sven', 'templar_assassin', 'terrorblade', 'tidehunter',
        'treant', 'troll_warlord', 'tusk', 'vengefulspirit', 'venomancer',
        'viper', 'void_spirit', 'windrunner'
    ]
    return sorted(heroes)

def check_template_coverage(templates_dir="custom_templates"):
    """Check which heroes we have templates for vs which we're missing."""
    all_heroes = get_all_underlords_heroes()
    
    templates_path = Path(templates_dir) / "templates"
    if not templates_path.exists():
        print(f"Templates directory not found: {templates_path}")
        return
    
    # Find existing templates
    existing_templates = []
    for template_file in templates_path.glob("*_template.png"):
        hero_name = template_file.stem.replace("_template", "")
        existing_templates.append(hero_name)
    
    existing_templates = sorted(existing_templates)
    missing_heroes = [hero for hero in all_heroes if hero not in existing_templates]
    
    print(f"\n{'='*60}")
    print("TEMPLATE COVERAGE REPORT")
    print(f"{'='*60}")
    print(f"Total heroes in Underlords: {len(all_heroes)}")
    print(f"Templates extracted: {len(existing_templates)}")
    print(f"Missing templates: {len(missing_heroes)}")
    print(f"Coverage: {len(existing_templates)/len(all_heroes)*100:.1f}%")
    
    if existing_templates:
        print(f"\n✅ Heroes with templates ({len(existing_templates)}):")
        for i, hero in enumerate(existing_templates):
            if i % 6 == 0:
                print()
            print(f"  {hero:<15}", end="")
        print()
    
    if missing_heroes:
        print(f"\n❌ Missing heroes ({len(missing_heroes)}):")
        for i, hero in enumerate(missing_heroes):
            if i % 6 == 0:
                print()
            print(f"  {hero:<15}", end="")
        print()
    
    return existing_templates, missing_heroes

def main():
    """Main function with example usage."""
    print("=== CUSTOM TEMPLATE EXTRACTOR ===")
    print("Extract hero templates from actual game screenshots")
    print()
    
    # Example usage
    example_mappings = {
        # Row 1
        "row1crew0": "luna",
        "row1crew1": "tusk", 
        "row1crew2": "pudge",
        
        # Row 2  
        "row2crew0": "treant",
        "row2crew1": "bounty_hunter",
        "row2crew2": "ember_spirit",
        
        # Add more as needed...
        # "row3crew0": "death_prophet",
        # "row1bench0": "mirana",
    }
    
    print("Example usage:")
    print("1. Specify a screenshot and hero mappings")
    print("2. Run the extraction")
    print("3. Check coverage")
    print()
    
    # Check if we have test screenshots
    test_screenshots = [
        "test/screenshot/screenshot01.png",
        "test/screenshot/screenshot02.png", 
        "test/screenshot/screenshot03.png"
    ]
    
    available_screenshots = [img for img in test_screenshots if os.path.exists(img)]
    
    if available_screenshots:
        print(f"Available test screenshots:")
        for img in available_screenshots:
            print(f"  - {img}")
        print()
        
        # Use the first available screenshot for demo
        screenshot = available_screenshots[0]
        print(f"Demo: Extracting templates from {screenshot}")
        print(f"Hero mappings: {example_mappings}")
        print()
        
        # Run extraction
        success = extract_templates_from_screenshot(screenshot, example_mappings)
        
        if success:
            # Check coverage
            check_template_coverage()
        
    else:
        print("No test screenshots found. Place screenshots in test/screenshot/ directory.")
        print()
        print("To use this script:")
        print("1. python create_custom_templates.py")
        print("2. Modify the hero_mappings in the script")
        print("3. Run multiple times with different screenshots")

if __name__ == "__main__":
    main() 