import cv2
import numpy as np
import os
from pathlib import Path
import sys
import pytesseract

# Configure Tesseract for faster processing
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TESSERACT_CONFIG = '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- '


def find_column_headers(image, header_start=61, header_end=93):
    """
    Optimized column header detection using exact header area (60px to 93px).
    Returns: (found_headers_dict, debug_image_with_headers_drawn)
    """
    from collections import Counter
    
    # Crop the exact header area (60px to 93px)
    header_img = image[header_start:header_end, :]
    
    # Create debug image from full image
    debug_img = image.copy()
    
    # Use Tesseract OCR with optimized config
    data = pytesseract.image_to_data(
        header_img, 
        output_type=pytesseract.Output.DICT, 
        config=TESSERACT_CONFIG
    )
    
    # Process headers in one pass
    found_headers = {}
    words = [text.strip().upper() for text in data['text']]
    n = len(words)
    
    # First pass: look for single words and potential NET WORTH combinations
    for i in range(n):
        # Try single word
        text_clean = words[i]
        if text_clean in ["PLAYER", "HEALTH", "RECORD", "CREW", "UNDERLORD", "BENCH"]:
            x, y, w, h = data['left'][i], data['top'][i] + header_start, data['width'][i], data['height'][i]
            found_headers[text_clean] = (x, y, w, h)
            # Draw rectangle around found header
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(debug_img, text_clean, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Try joining with next word for NET WORTH
        if i < n - 1:
            # Try different combinations for NET WORTH
            possible_combinations = [
                f"{words[i]} {words[i+1]}",  # Standard "NET WORTH"
                f"{words[i]}{words[i+1]}",   # No space
                f"{words[i]}-{words[i+1]}",  # With hyphen
                words[i] + words[i+1]        # Concatenated
            ]
            
            for joined in possible_combinations:
                if joined.replace(" ", "").replace("-", "") == "NETWORTH":
                    # Combine bounding boxes
                    x = min(data['left'][i], data['left'][i+1])
                    y = min(data['top'][i], data['top'][i+1]) + header_start
                    w = max(data['left'][i]+data['width'][i], data['left'][i+1]+data['width'][i+1]) - x
                    h = max(data['top'][i]+data['height'][i], data['top'][i+1]+data['height'][i+1]) - min(data['top'][i], data['top'][i+1])
                    found_headers["NET WORTH"] = (x, y, w, h)
                    # Draw rectangle around NET WORTH
                    cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(debug_img, "NET WORTH", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    break
    
    # Second pass: look for NET WORTH as a single word
    for i in range(n):
        text_clean = words[i].replace(" ", "").replace("-", "")
        if text_clean == "NETWORTH":
            x, y, w, h = data['left'][i], data['top'][i] + header_start, data['width'][i], data['height'][i]
            found_headers["NET WORTH"] = (x, y, w, h)
            # Draw rectangle around NET WORTH
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(debug_img, "NET WORTH", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Filter headers by y-position
    if found_headers:
        ys = [y for (x, y, w, h) in found_headers.values()]
        most_common_y, _ = Counter(ys).most_common(1)[0]
        found_headers = {
            header: (x, y, w, h) 
            for header, (x, y, w, h) in found_headers.items() 
            if abs(y - most_common_y) < 15 and w < 500
        }
    
    # Save debug images
    os.makedirs('output/debug', exist_ok=True)
    
    # Save the cropped header area for verification
    header_crop_path = 'output/debug/header_crop_60_93.png'
    cv2.imwrite(header_crop_path, header_img)
    print(f"Saved header crop (60px-93px) to {header_crop_path}")
    
    # Save full image with header detection rectangles
    debug_path = 'output/debug/header_detection_test.png'
    cv2.imwrite(debug_path, debug_img)
    print(f"Saved header detection debug image to {debug_path}")
    
    return found_headers, debug_img

def get_fixed_row_boundaries():
    """
    Fast, hardcoded row boundaries for standard Underlords screenshots.
    
    Header: y=60 to y=93 (33px high)
    Each row: 80px high
    8 player rows total
    
    Returns row start positions: [93, 173, 253, 333, 413, 493, 573, 653, 733]
    
    NOTE: Change back to find_row_boundaries() if dynamic detection needed 
    """
    header_end = 93 
    row_height = 80
    return [header_end + (i * row_height) for i in range(9)]  # 8 rows + end boundary

def calculate_hero_slots(crew_start_x, crew_end_x, hero_width=56, center_spacing=80, max_slots=None):
    """
    Calculate hero slot positions within a column.
    
    Layout:
    - First hero center: 28px from column start (56px/2)
    - Each subsequent center: 80px apart
    - Hero width: 56px (±28px from center)
    
    Args:
        crew_start_x: Start x position of column
        crew_end_x: End x position of column
        hero_width: Width of each hero slot in pixels (default 56px)
        center_spacing: Distance between hero centers (default 80px)
        max_slots: Maximum number of slots (None for unlimited, 8 for bench)
    
    Returns:
        List of (start_x, end_x, center_x) tuples for each slot
    """
    first_center_offset = hero_width // 2  # 28px from column start
    half_hero_width = hero_width // 2      # 28px
    
    slots = []
    slot_index = 0
    
    while True:
        # Check max slots limit first
        if max_slots is not None and slot_index >= max_slots:
            break
            
        # Calculate center position
        center_x = crew_start_x + first_center_offset + (slot_index * center_spacing)
        
        # Calculate slot boundaries
        slot_start = center_x - half_hero_width
        slot_end = center_x + half_hero_width
        
        # Check if slot fits within column
        if slot_end > crew_end_x:
            break
            
        slots.append((slot_start, slot_end, center_x))
        slot_index += 1
    
    return slots

def test_hero_slots(image_path, output_path="output/debug/test_hero_slots_debug.png"):
    """
    Test and visualize hero slot calculations on a screenshot.
    """
    print(f"Testing hero slots on: {image_path}")
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Failed to load image: {image_path}")
        return None
    
    # Find column headers (this will also create the debug image with header rectangles)
    print("Finding column headers...")
    headers, debug_image = find_column_headers(image)
    
    if not headers:
        print("No headers found")
        return None
    
    print(f"Found headers: {list(headers.keys())}")
    
    # Get column positions
    crew_start_x = None
    crew_end_x = None
    bench_start_x = None
    
    if 'CREW' in headers:
        crew_start_x = headers['CREW'][0]
        print(f"CREW column starts at x={crew_start_x}")
    
    if 'UNDERLORD' in headers:
        crew_end_x = headers['UNDERLORD'][0]
        print(f"CREW column ends at UNDERLORD x={crew_end_x}")
    elif 'BENCH' in headers:
        crew_end_x = headers['BENCH'][0]
        print(f"CREW column ends at BENCH x={crew_end_x}")
    
    if 'BENCH' in headers:
        bench_start_x = headers['BENCH'][0]
        print(f"BENCH column starts at x={bench_start_x}")
    
    # Calculate crew slots if we have the boundaries (no max limit for crew)
    crew_slots = []
    if crew_start_x is not None and crew_end_x is not None:
        crew_slots = calculate_hero_slots(crew_start_x, crew_end_x)
        print(f"Calculated {len(crew_slots)} CREW slots:")
        for i, (start, end, center) in enumerate(crew_slots):
            print(f"  Slot {i+1}: x={start} to x={end} (center={center}, width={end-start}px)")
    
    # Calculate bench slots if we have bench column (max 8 heroes)
    bench_slots = []
    if bench_start_x is not None:
        # Assume bench goes to right edge of image, but limit to 8 slots max
        bench_end_x = image.shape[1]
        bench_slots = calculate_hero_slots(bench_start_x, bench_end_x, max_slots=8)
        print(f"Calculated {len(bench_slots)} BENCH slots (max 8):")
        for i, (start, end, center) in enumerate(bench_slots):
            print(f"  Slot {i+1}: x={start} to x={end} (center={center}, width={end-start}px)")
    
    # Get row boundaries for visualization
    row_starts = get_fixed_row_boundaries()
    print(f"Using row boundaries: {row_starts}")
    
    # Draw visualization
    colors = [
        (0, 255, 0),    # Green for crew slots
        (255, 0, 0),    # Blue for bench slots
        (0, 255, 255),  # Yellow for column boundaries
        (255, 255, 255) # White for row boundaries
    ]
    
    # Draw row boundaries
    for i, y in enumerate(row_starts):
        cv2.line(debug_image, (0, y), (image.shape[1], y), colors[3], 1)
        cv2.putText(debug_image, f"Row {i}", (10, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors[3], 1)
    
    # Draw column boundaries
    if crew_start_x is not None:
        cv2.line(debug_image, (crew_start_x, 0), (crew_start_x, image.shape[0]), colors[2], 2)
        cv2.putText(debug_image, "CREW START", (crew_start_x+5, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[2], 2)
    
    if crew_end_x is not None:
        cv2.line(debug_image, (crew_end_x, 0), (crew_end_x, image.shape[0]), colors[2], 2)
        cv2.putText(debug_image, "CREW END", (crew_end_x+5, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[2], 2)
    
    if bench_start_x is not None:
        cv2.line(debug_image, (bench_start_x, 0), (bench_start_x, image.shape[0]), colors[2], 2)
        cv2.putText(debug_image, "BENCH START", (bench_start_x+5, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[2], 2)
    
    # Draw crew slots for each row
    for row_idx in range(len(row_starts)-1):
        row_start = row_starts[row_idx]
        row_end = row_starts[row_idx + 1]
        
        # Draw crew slots
        for slot_idx, (slot_start, slot_end, slot_center) in enumerate(crew_slots):
            # Draw slot rectangle
            cv2.rectangle(debug_image, 
                         (slot_start, row_start), 
                         (slot_end, row_end), 
                         colors[0], 1)
            
            # Draw slot center line
            cv2.line(debug_image, 
                    (slot_center, row_start), 
                    (slot_center, row_end), 
                    colors[0], 1)  # Thicker line for center
            
            # Label slot with center position
            if row_idx == 0:  # Only label first row to avoid clutter
                cv2.putText(debug_image, f"C{slot_idx+1}:{slot_center}", 
                           (slot_start+2, row_start+15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, colors[0], 1)
        
        # Draw bench slots
        for slot_idx, (slot_start, slot_end, slot_center) in enumerate(bench_slots):
            # Draw slot rectangle
            cv2.rectangle(debug_image, 
                         (slot_start, row_start), 
                         (slot_end, row_end), 
                         colors[1], 1)
            
            # Draw slot center line
            cv2.line(debug_image, 
                    (slot_center, row_start), 
                    (slot_center, row_end), 
                    colors[1], 1)  # Thicker line for center
            
            # Label slot with center position
            if row_idx == 0:  # Only label first row to avoid clutter
                cv2.putText(debug_image, f"B{slot_idx+1}:{slot_center}", 
                           (slot_start+2, row_start+15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, colors[1], 1)
    
    # Add legend
    legend_y = 20
    cv2.putText(debug_image, "GREEN: CREW slots", (10, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[0], 2)
    cv2.putText(debug_image, "BLUE: BENCH slots (max 8)", (10, legend_y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[1], 2)
    cv2.putText(debug_image, "YELLOW: Column boundaries", (10, legend_y+40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[2], 2)
    cv2.putText(debug_image, "WHITE: Row boundaries", (10, legend_y+60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, colors[3], 2)
    
    # Save debug image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, debug_image)
    print(f"Saved slot visualization to: {output_path}")
    
    # Return slot information for further analysis
    return {
        'crew_slots': crew_slots,
        'bench_slots': bench_slots,
        'crew_column': (crew_start_x, crew_end_x),
        'bench_column': (bench_start_x, image.shape[1] if bench_start_x else None),
        'row_boundaries': row_starts
    }

def main():
    # Default to a test screenshot, or use command line argument
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Look for test screenshots
        test_images = [
            "test/screenshot/screenshot03.png"
        ]
        
        image_path = None
        for test_img in test_images:
            if os.path.exists(test_img):
                image_path = test_img
                break
        
        if not image_path:
            print("No test image found. Please provide path as argument:")
            print("python test_hero_slots.py <image_path>")
            return
    
    print(f"Testing hero slot calculations...")
    print(f"Input image: {image_path}")
    
    result = test_hero_slots(image_path)
    
    if result:
        print("\n=== SLOT CALCULATION RESULTS ===")
        print(f"CREW slots: {len(result['crew_slots'])}")
        print(f"BENCH slots: {len(result['bench_slots'])}")
        print(f"CREW column: {result['crew_column']}")
        print(f"BENCH column: {result['bench_column']}")
        print("\nCheck the generated 'output/debug/test_hero_slots_debug.png' image to verify slot alignment!")
    else:
        print("Failed to calculate slots")

if __name__ == "__main__":
    main() 