import cv2
import os
from components.utils import get_row_boundaries, AnalysisConfig, load_and_preprocess_image

# Player column position constants
PLAYER_COLUMN_X_START = 28
PLAYER_COLUMN_X_END = 308
PLAYER_ROW_HEIGHT = 80
PLAYER_IMAGE_X_START = 28
PLAYER_IMAGE_X_END = 108
PLAYER_NAME_X_START = 120
PLAYER_NAME_Y_START = 14
NAME_HEIGHT = 24
PLAYER_INFO_X_START = 120
PLAYER_INFO_Y_START = 39
PLAYER_INFO_HEIGHT = 20
PLAYER_INFO_X_END = 178
ROWS_START_Y = 96

class DigitTemplateCreator:
    """Utility class for creating digit templates from screenshots."""
    
    def __init__(self, debug=False):
        self.debug = debug
    
    def _convert_to_binary(self, image):
        """Convert image to binary for consistent template matching."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return binary
    
    def extract_player_gold_region(self, image, row_y):
        """Extract the player gold region (after first 24px) from a row."""
        
        info_y_start = row_y + PLAYER_INFO_Y_START
        info_y_end = info_y_start + PLAYER_INFO_HEIGHT
        
        # Gold is in the rest of the region (after first 24px)
        gold_region = image[info_y_start:info_y_end, PLAYER_INFO_X_START + 24:PLAYER_INFO_X_END]
        
        return gold_region
    
    def extract_all_gold_areas(self, image, output_dir="assets/gold_areas_to_crop"):
        """Extract and save all gold areas from all players for manual cropping."""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get row boundaries
        row_boundaries = get_row_boundaries()
        
        saved_count = 0
        
        for row_num, row_y in enumerate(row_boundaries):
            # Extract gold region for this row
            gold_region = self.extract_player_gold_region(image, row_y)
            
            if gold_region.size > 0:
                # Convert to binary for consistency with template matching
                gold_region_binary = self._convert_to_binary(gold_region)
                
                # Save the binary gold region as an image
                output_path = os.path.join(output_dir, f"gold_area_row_{row_num}.png")
                cv2.imwrite(output_path, gold_region_binary)
                saved_count += 1
                
                if self.debug:
                    print(f"Saved binary gold area for row {row_num}: {output_path}")
        
        print(f"Extracted {saved_count} binary gold areas to {output_dir}")
        print("You can now manually crop these images to create digit templates:")
        print("1. Open each image in paint")
        print("2. Crop to show only one digit")
        print("3. Save as assets/templates/digits/digit_X.png (where X is the digit)")
        
        return saved_count
    
    def save_digit_template_manually(self, image, row_y, digit_value):
        """Manually save a digit template using the entire gold area."""
        gold_region = self.extract_player_gold_region(image, row_y)
        
        if gold_region.size > 0:
            # Save digit template directly
            if digit_value < 0 or digit_value > 9:
                return False
            
            template_path = os.path.join("assets/templates/digits", f"digit_{digit_value}.png")
            if os.path.exists(template_path):
                return False  # Don't overwrite existing template
            
            # Save template
            digit_image_binary = self._convert_to_binary(gold_region)
            cv2.imwrite(template_path, digit_image_binary)
            
            if self.debug:
                print(f"Manually saved digit template for digit {digit_value}")
            return True
        
        return False

def extract_gold_areas_for_templates(image_path, output_dir="assets/gold_areas_to_crop"):
    """Extract all gold areas from a screenshot for manual template creation."""
    config = AnalysisConfig(debug=True)
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is not None:
        creator = DigitTemplateCreator(debug=config.debug)
        count = creator.extract_all_gold_areas(image, output_dir)
        return count
    else:
        print(f"Failed to load image: {image_path}")
        return 0

if __name__ == "__main__":
    # Extract gold areas for template creation
    print("=== EXTRACTING GOLD AREAS FOR TEMPLATES ===")
    image_path = "assets/templates/screenshots_for_templates/SS_07.png"
    count = extract_gold_areas_for_templates(image_path)
    print(f"Extracted {count} gold areas. Check assets/gold_areas_to_crop/ folder.") 