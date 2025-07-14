import cv2
import pytesseract
from collections import Counter
import os

# Configure Tesseract for faster processing
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
TESSERACT_CONFIG = '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz- '

def find_column_headers_complete(image, header_start=61, header_end=93):
    """
    Complete column header detection for all Underlords headers.
    Expected headers: PLAYER, HEALTH, RECORD, NET WORTH, ALLIANCES, CREW, UNDERLORD, CONTRAPTIONS, BENCH
    
    Args:
        image: Input image
        header_start: Y coordinate where header area starts
        header_end: Y coordinate where header area ends
        
    Returns:
        Tuple of (found_headers_dict, debug_image)
        found_headers_dict: {header_name: (x, y, w, h), ...}
    """
    # Crop the exact header area
    header_img = image[header_start:header_end, :]
    
    # Create debug image
    debug_img = image.copy()
    
    # Use Tesseract OCR
    data = pytesseract.image_to_data(
        header_img, 
        output_type=pytesseract.Output.DICT, 
        config=TESSERACT_CONFIG
    )
    
    # Process all detected text
    found_headers = {}
    words = [text.strip().upper() for text in data['text']]
    n = len(words)
    
    # Expected single word headers
    single_headers = ["PLAYER", "HEALTH", "RECORD", "ALLIANCES", "CREW", "UNDERLORD", "CONTRAPTIONS", "BENCH"]
    
    # Find single word headers
    for i in range(n):
        text_clean = words[i]
        if text_clean in single_headers:
            x, y, w, h = data['left'][i], data['top'][i] + header_start, data['width'][i], data['height'][i]
            found_headers[text_clean] = (x, y, w, h)
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(debug_img, text_clean, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Find NET WORTH (two words)
    for i in range(n - 1):
        if words[i] in ["NET", "net"] and words[i + 1] in ["WORTH", "worth"]:
            # Combine bounding boxes
            x = min(data['left'][i], data['left'][i+1])
            y = min(data['top'][i], data['top'][i+1]) + header_start
            w = max(data['left'][i]+data['width'][i], data['left'][i+1]+data['width'][i+1]) - x
            h = max(data['top'][i]+data['height'][i], data['top'][i+1]+data['height'][i+1]) - min(data['top'][i], data['top'][i+1])
            found_headers["NET WORTH"] = (x, y, w, h)
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(debug_img, "NET WORTH", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            break
    
    # Look for NET WORTH as single word (NETWORTH)
    for i in range(n):
        text_clean = words[i].replace(" ", "").replace("-", "")
        if text_clean in ["NETWORTH", "networth"]:
            x, y, w, h = data['left'][i], data['top'][i] + header_start, data['width'][i], data['height'][i]
            found_headers["NET WORTH"] = (x, y, w, h)
            cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(debug_img, "NET WORTH", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    # Filter headers by y-position (remove outliers)
    if found_headers:
        ys = [y for (x, y, w, h) in found_headers.values()]
        most_common_y, _ = Counter(ys).most_common(1)[0]
        found_headers = {
            header: (x, y, w, h) 
            for header, (x, y, w, h) in found_headers.items() 
            if abs(y - most_common_y) < 15 and w < 500
        }
    
    return found_headers, debug_img

def get_crew_and_bench_boundaries(headers):
    """
    Extract CREW and BENCH column boundaries from detected headers.
    
    Args:
        headers: Dict from find_column_headers_complete()
        
    Returns:
        Tuple of (crew_start_x, crew_end_x, bench_start_x)
    """
    crew_start_x = None
    crew_end_x = None
    bench_start_x = None
    
    # Find CREW column - headers returns (x, y, w, h) tuples
    if 'CREW' in headers:
        crew_start_x = headers['CREW'][0]  # x position from (x, y, w, h)
        
        # CREW ends where UNDERLORD begins
        if 'UNDERLORD' in headers:
            crew_end_x = headers['UNDERLORD'][0]  # x position
    
    # Find BENCH column
    if 'BENCH' in headers:
        bench_start_x = headers['BENCH'][0]  # x position from (x, y, w, h)
    
    return crew_start_x, crew_end_x, bench_start_x 