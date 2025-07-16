import cv2
import time

class AnalysisConfig:
    """Configuration for the analysis process."""
    def __init__(self, debug=False, show_timing=True, show_visualization=False):
        self.debug = debug
        self.show_timing = show_timing
        self.show_visualization = show_visualization

def get_row_boundaries(header_end=93, row_height=80, num_rows=8):
    """Returns row start positions: [93, 173, 253, 333, 413, 493, 573, 653, 733]"""
    return [header_end + (i * row_height) for i in range(num_rows)]  # 8 rows

def load_and_preprocess_image(image_path, config):
    """Load and preprocess the image."""
    if config.debug:
        print("Loading image...")

    image = cv2.imread(image_path)
    if image is None:
        print(f"Failed to load image: {image_path}")
        return None, None
    
    # Convert to grayscale first, then apply binary threshold
    # Lower threshold (110) to capture brown/yellow 1-star heroes
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh_binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    return image, thresh_binary

def get_header_positions(image, template_folder="assets/templates/header_templates"):
    """Get x positions of headers using template matching."""
    import os
    import glob
    
    _, thresh = cv2.threshold(image, 100, 255, cv2.THRESH_BINARY)
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
        template = cv2.imread(template_file)
        if len(template.shape) == 3:
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        
        # Match template
        result = cv2.matchTemplate(header_region, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= 0.7:  # Good match
            positions[header_name] = max_loc[0]
    
    # Sort by x position
    return dict(sorted(positions.items(), key=lambda x: x[1])) 