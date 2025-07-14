import cv2
import os
import glob


def get_header_positions(image_path, template_folder="header_templates"):
    """Get x positions of headers using template matching."""
    
    # Load image
    image = cv2.imread(image_path)
    _, thresh = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
    header_region = thresh[61:93, :]  # Header area
    
    if len(header_region.shape) == 3:
        header_region = cv2.cvtColor(header_region, cv2.COLOR_BGR2GRAY)
    
    positions = {}
    
    # Find all template files
    template_files = glob.glob(os.path.join(template_folder, "*_template.png"))
    
    for template_file in template_files:
        # Get header name from filename
        header_name = os.path.basename(template_file).replace("_template.png", "").upper()
        
        # Load template
        template = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
        
        # Match template
        result = cv2.matchTemplate(header_region, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= 0.7:  # Good match
            positions[header_name] = max_loc[0]
    
    # Sort by x position
    return dict(sorted(positions.items(), key=lambda x: x[1]))


if __name__ == "__main__":
    import sys
    
    image_path = sys.argv[1] if len(sys.argv) > 1 else "test/screenshot/screenshot14.png"
    
    positions = get_header_positions(image_path)
    
    for header, x_pos in positions.items():
        print(f"{header}: {x_pos}") 