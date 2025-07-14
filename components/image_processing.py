import cv2
import pytesseract
import numpy as np
import os
import json

# Configure Tesseract for faster processing
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Different Tesseract configurations to try
TESSERACT_CONFIGS = {
    'default': '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- ',
    'single_line': '--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- ',
    'single_word': '--psm 8 --oem 1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- ',
    'raw_line': '--psm 13 --oem 1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- ',
    'with_spacing': '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- -c preserve_interword_spaces=1',
    'legacy_engine': '--psm 6 --oem 0 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- ',
    'neural_only': '--psm 6 --oem 2 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- ',
    'word_confident': '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- -c tessedit_min_orientation_margin=7'
}

# Default configuration (for backwards compatibility)
TESSERACT_CONFIG = TESSERACT_CONFIGS['with_spacing']

def find_column_headers(image, header_start=61, header_end=93, debug=False, debug_img=False):
    """
    Complete column header detection for all Underlords headers.
    Expected headers: PLAYER, HEALTH, RECORD, NET WORTH, ALLIANCES, CREW, UNDERLORD, CONTRAPTIONS, BENCH
    
    Args:
        image: Input image
        header_start: Y coordinate where header area starts
        header_end: Y coordinate where header area ends
        debug: Whether to print debug text output (default: False)
        debug_img: Whether to create and return debug image (default: False)
        
    Returns:
        If debug_img=True: Tuple of (found_headers_dict, debug_image)
        If debug_img=False: found_headers_dict only
        found_headers_dict: {header_name: (x, y, w, h), ...}
    """
    # Crop the exact header area
    header_img = image[header_start:header_end, :]
    
    # Create debug image only if debug_img mode is enabled
    debug_image = None
    if debug_img:
        debug_image = image.copy()
    
    # Use Tesseract OCR
    data = pytesseract.image_to_data(
        header_img, 
        output_type=pytesseract.Output.DICT, 
        config=TESSERACT_CONFIG
    )
    
    # Debug output: Show all detected text
    if debug:
        print("\n=== TESSERACT DEBUG OUTPUT ===")
        print("Raw text detected by Tesseract:")
        for i, text in enumerate(data['text']):
            if text.strip():  # Only show non-empty text
                confidence = data['conf'][i]
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                print(f"  '{text}' (confidence: {confidence}, pos: {x},{y}, size: {w}x{h})")
        print("=" * 30)
    
    # Process all detected text
    found_headers = {}
    words = [text.strip().upper() for text in data['text']]
    n = len(words)
    
    if debug:
        print(f"Processed words: {[word for word in words if word]}")
    
    # Expected single word headers
    single_headers = ["PLAYER", "HEALTH", "RECORD", "NETWORTH", "ALLIANCES", "CREW", "UNDERLORD", "CONTRAPTIONS", "BENCH"]
    
    # Find single word headers
    for i in range(n):
        text_clean = words[i]
        if text_clean in single_headers:
            x, y, w, h = data['left'][i], data['top'][i] + header_start, data['width'][i], data['height'][i]
            found_headers[text_clean] = (x, y, w, h)
            
            if debug:
                print(f"✓ Found header: '{text_clean}' at ({x}, {y})")
            
            # Only draw debug info if debug_img mode is enabled
            if debug_img and debug_image is not None:
                cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(debug_image, text_clean, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    if debug:
        print(f"Total headers found: {len(found_headers)}")
        print(f"Headers found: {list(found_headers.keys())}")
        expected_headers = single_headers
        missing_headers = [h for h in expected_headers if h not in found_headers]
        if missing_headers:
            print(f"Missing headers: {missing_headers}")
        print("=" * 30)
    
    # Return based on debug_img mode
    if debug_img:
        return found_headers, debug_image
    else:
        return found_headers

def create_slot_mask(slot_image, sample_x=3, sample_y=3, tolerance=2, crop_size=28):
    """
    Create a mask from a hero slot by detecting background color.
    
    Args:
        slot_image: Hero slot image (56x56 or 28x28)
        sample_x, sample_y: Position to sample background color from
        tolerance: Color tolerance for matching
        crop_size: Size to crop to (default 28x28)
        
    Returns:
        mask: 255 = hero pixels (use), 0 = background pixels (ignore)
    """
    # Crop to top-left region if needed
    if slot_image.shape[0] > crop_size or slot_image.shape[1] > crop_size:
        slot_crop = slot_image[:crop_size, :crop_size]
    else:
        slot_crop = slot_image
    
    h, w = slot_crop.shape[:2]
    
    # Sample background color from the slot
    bg_color_bgr = tuple(slot_crop[sample_y, sample_x].astype(int))
    
    # Create color range for background removal
    lower_bound = np.array([max(0, c - tolerance) for c in bg_color_bgr])
    upper_bound = np.array([min(255, c + tolerance) for c in bg_color_bgr])
    
    # Find background pixels
    bg_mask = cv2.inRange(slot_crop, lower_bound, upper_bound)
    
    # Create mask: background pixels = 0 (ignore), non-background = 255 (use)
    mask = np.where(bg_mask > 0, 0, 255).astype(np.uint8)
    
    return mask

def create_slots_masks(image, slots_by_row, sample_x=3, sample_y=3, tolerance=2, crop_size=28):
    """
    Create masks for all slots organized by row.
    
    Args:
        image: Original game image
        slots_by_row: Dict of {row_num: [slot_dicts]} where each slot has x_start, y_start, etc.
        sample_x, sample_y: Position to sample background color from
        tolerance: Color tolerance for matching
        crop_size: Size to crop to (default 28x28)
        
    Returns:
        Dict of {row_num: [masks]} where each mask corresponds to a slot in the same position
    """
    masks_by_row = {}
    
    for row_num, slots in slots_by_row.items():
        row_masks = []
        
        for slot in slots:
            # Extract slot image from main image
            slot_image = image[slot['y_start']:slot['y_end'], slot['x_start']:slot['x_end']]
            
            # Skip if slot image is empty or wrong size
            if slot_image.size == 0 or slot_image.shape[0] == 0 or slot_image.shape[1] == 0:
                row_masks.append(None)
                continue
                
            # Create mask for this slot
            mask = create_slot_mask(slot_image, sample_x, sample_y, tolerance, crop_size)
            row_masks.append(mask)
        
        masks_by_row[row_num] = row_masks
    
    return masks_by_row

def create_all_slots_masks(image, crew_slots_by_row, bench_slots_by_row, **mask_params):
    """
    Create masks for both crew and bench slots organized by row.
    
    Args:
        image: Original game image
        crew_slots_by_row: Dict of {row_num: [crew_slots]}
        bench_slots_by_row: Dict of {row_num: [bench_slots]}
        **mask_params: Parameters to pass to create_slot_mask
        
    Returns:
        Tuple of (crew_masks_by_row, bench_masks_by_row)
    """
    crew_masks_by_row = create_slots_masks(image, crew_slots_by_row, **mask_params)
    bench_masks_by_row = create_slots_masks(image, bench_slots_by_row, **mask_params)
    
    return crew_masks_by_row, bench_masks_by_row

def load_template_masks(masks_folder="assets/templates/hero_masks", debug=False):
    """
    Load all template masks from the masks folder.
    
    Args:
        masks_folder: Path to folder containing template masks
        debug: Whether to print debug information
        
    Returns:
        Dict of {hero_name: mask_image}
    """
    import glob
    
    template_masks = {}
    
    # Find all mask files in the folder
    mask_files = glob.glob(os.path.join(masks_folder, "*.png"))
    
    for mask_file in mask_files:
        # Extract hero name from filename (remove _mask.png)
        filename = os.path.basename(mask_file)
        hero_name = filename.replace("_mask.png", "")
        
        # Load the mask
        mask = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
        if mask is not None:
            template_masks[hero_name] = mask
        else:
            if debug:
                print(f"Warning: Could not load mask {mask_file}")
    
    if debug:
        print(f"Loaded {len(template_masks)} template masks")
    return template_masks

def compare_mask_to_templates(slot_mask, template_masks, method=cv2.TM_CCOEFF_NORMED, threshold=0.3):
    """
    Compare a slot mask against all template masks to find the best match.
    
    Args:
        slot_mask: Generated mask from a slot
        template_masks: Dict of {hero_name: template_mask}
        method: OpenCV template matching method
        threshold: Minimum confidence threshold
        
    Returns:
        Tuple of (best_hero_name, confidence) or (None, 0) if no good match
    """
    if slot_mask is None:
        return None, 0.0
    
    best_match = None
    best_confidence = 0.0
    
    for hero_name, template_mask in template_masks.items():
        # Resize template to match slot mask size if needed
        if template_mask.shape != slot_mask.shape:
            template_resized = cv2.resize(template_mask, (slot_mask.shape[1], slot_mask.shape[0]))
        else:
            template_resized = template_mask
        
        # Perform template matching
        result = cv2.matchTemplate(slot_mask, template_resized, method)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        
        # For TM_CCOEFF_NORMED, higher values are better matches
        confidence = max_val
        
        if confidence > best_confidence and confidence >= threshold:
            best_confidence = confidence
            best_match = hero_name
    
    return best_match, best_confidence

def is_mask_empty(mask):
    """
    Check if a mask is completely black (empty slot).
    
    Args:
        mask: Mask image to check
        
    Returns:
        True if mask is completely black (empty), False otherwise
    """
    if mask is None:
        return True
    
    # Check if all pixels are 0 (black)
    return np.all(mask == 0)

def analyze_all_masks(crew_masks_by_row, bench_masks_by_row, template_masks, debug=False):
    """
    Analyze all generated masks against template masks to identify heroes.
    Stops analyzing a row when an empty (black) mask is found.
    
    Args:
        crew_masks_by_row: Dict of {row_num: [crew_masks]}
        bench_masks_by_row: Dict of {row_num: [bench_masks]}
        template_masks: Dict of {hero_name: template_mask}
        debug: Whether to print debug information
        
    Returns:
        Tuple of (crew_results, bench_results)
        crew_results: Dict of {row_num: [{"hero_name": str, "confidence": float}, ...]}
        bench_results: Dict of {row_num: [{"hero_name": str, "confidence": float}, ...]}
    """
    crew_results = {}
    bench_results = {}
    
    # Analyze crew masks
    for row_num, masks in crew_masks_by_row.items():
        row_results = []
        for slot_idx, mask in enumerate(masks):
            # Check if mask is empty (completely black)
            if is_mask_empty(mask):
                if debug:
                    print(f"Crew Row {row_num}, Slot {slot_idx}: Empty slot detected - skipping remaining slots in row")
                # Add empty dict for this slot and all remaining slots
                remaining_slots = len(masks) - slot_idx
                row_results.extend([{"hero_name": None, "confidence": 0.0}] * remaining_slots)
                break
            
            # Compare mask to templates
            hero_name, confidence = compare_mask_to_templates(mask, template_masks)
            
            # Create hero dictionary
            hero_dict = {
                "hero_name": hero_name,
                "confidence": confidence
            }
            row_results.append(hero_dict)
            
            if debug:
                if hero_name:
                    print(f"Crew Row {row_num}, Slot {slot_idx}: {hero_name} ({confidence:.3f})")
                else:
                    print(f"Crew Row {row_num}, Slot {slot_idx}: No match")
        
        crew_results[row_num] = row_results
    
    # Analyze bench masks
    for row_num, masks in bench_masks_by_row.items():
        row_results = []
        for slot_idx, mask in enumerate(masks):
            # Check if mask is empty (completely black)
            if is_mask_empty(mask):
                if debug:
                    print(f"Bench Row {row_num}, Slot {slot_idx}: Empty slot detected - skipping remaining slots in row")
                # Add empty dict for this slot and all remaining slots
                remaining_slots = len(masks) - slot_idx
                row_results.extend([{"hero_name": None, "confidence": 0.0}] * remaining_slots)
                break
            
            # Compare mask to templates
            hero_name, confidence = compare_mask_to_templates(mask, template_masks)
            
            # Create hero dictionary
            hero_dict = {
                "hero_name": hero_name,
                "confidence": confidence
            }
            row_results.append(hero_dict)
            
            if debug:
                if hero_name:
                    print(f"Bench Row {row_num}, Slot {slot_idx}: {hero_name} ({confidence:.3f})")
                else:
                    print(f"Bench Row {row_num}, Slot {slot_idx}: No match")
        
        bench_results[row_num] = row_results
    
    return crew_results, bench_results

# ===== TEMPLATE MATCHING FOR HEADERS =====

def load_header_templates(template_folder="header_templates"):
    """
    Load header templates from folder for fast header detection.
    
    Args:
        template_folder: Path to folder containing header templates
        
    Returns:
        Dict of {header_name: template_image} or empty dict if no templates found
    """
    metadata_path = os.path.join(template_folder, "template_metadata.json")
    
    if not os.path.exists(metadata_path):
        return {}
    
    try:
        # Load metadata
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Load template images
        templates = {}
        for header_name, info in metadata.items():
            template_path = info['path']
            if os.path.exists(template_path):
                template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    templates[header_name] = template
        
        return templates
    except (json.JSONDecodeError, KeyError, IOError):
        return {}

def find_column_headers_fast(image, header_start=61, header_end=93, template_folder="header_templates", 
                           fallback_to_ocr=True, debug=False):
    """
    Fast header detection using template matching - much faster than OCR.
    Falls back to OCR if templates are not available.
    
    Args:
        image: Input image (same as OCR version)
        header_start: Y coordinate where header area starts
        header_end: Y coordinate where header area ends
        template_folder: Folder containing header templates
        fallback_to_ocr: Whether to use OCR if templates are not found
        debug: Whether to print debug information
        
    Returns:
        Dict of {header_name: (x, y, w, h)} - same format as OCR version
    """
    # Load templates     
    templates = load_header_templates(template_folder)
    
    if not templates:
        if fallback_to_ocr:
            if debug:
                print("No header templates found, falling back to OCR method...")
            return find_column_headers(image, header_start, header_end, debug=debug, debug_img=False)
        else:
            if debug:
                print("No header templates found and fallback disabled.")
            return {}    
    
    if debug:
        print(f"Using template matching with {len(templates)} templates")
    
    # Apply same preprocessing as OCR version
    if len(image.shape) == 3:
        _, thresh_binary = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
    else:
        thresh_binary = image
    
    # Extract header region  
    header_region = thresh_binary[header_start:header_end, :]
    if len(header_region.shape) == 3:
        header_region = cv2.cvtColor(header_region, cv2.COLOR_BGR2GRAY)
    
    found_headers = {}
    
    # Use template matching with high threshold for accuracy
    for header_name, template in templates.items():
        result = cv2.matchTemplate(header_region, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= 0.7:  # High confidence threshold
            template_h, template_w = template.shape
            x = max_loc[0]
            y = max_loc[1] + header_start
            found_headers[header_name] = (x, y, template_w, template_h)
            
            if debug:
                print(f"Found {header_name}: x={x}, y={y}, confidence={max_val:.3f}")
        elif debug:
            print(f"{header_name}: No match (best: {max_val:.3f})")
    
    return found_headers

def find_column_headers_with_timing(image, header_start=61, header_end=93, use_templates=True, debug=False):
    """
    Header detection with timing comparison between template matching and OCR.
    
    Args:
        image: Input image
        header_start: Y coordinate where header area starts
        header_end: Y coordinate where header area ends
        use_templates: Whether to try template matching first
        debug: Whether to print debug information
        
    Returns:
        Tuple of (found_headers, method_used, processing_time)
    """
    import time
    
    if use_templates:
        # Try template matching first
        start_time = time.time()
        headers = find_column_headers_fast(image, header_start, header_end, 
                                         fallback_to_ocr=False, debug=debug)
        template_time = time.time() - start_time
        
        if headers:
            if debug:
                print(f"Template matching found {len(headers)} headers in {template_time:.4f}s")
            return headers, "template_matching", template_time
        elif debug:
            print(f"Template matching failed, trying OCR...")
    
    # Fall back to OCR
    start_time = time.time()
    headers = find_column_headers(image, header_start, header_end, debug=debug, debug_img=False)
    ocr_time = time.time() - start_time
    
    if debug:
        print(f"OCR found {len(headers)} headers in {ocr_time:.4f}s")
    
    return headers, "ocr", ocr_time