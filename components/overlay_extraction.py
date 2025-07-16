import cv2
import numpy as np
import os
import glob
from components.shared_digit_detector import shared_detector
from components.player_template_manager import PlayerTemplateManager

# Overlay digit templates
LEVEL_GOLD_TEMPLATE_DIR = "assets/templates/digits"
HEALTH_TEMPLATE_DIR = "assets/templates/digits"

# Overlay coordinates and layout
OVERLAY_X = 100
OVERLAY_Y = 100
ROW_HEIGHT = 64
NUM_PLAYERS = 8
GAP_BETWEEN_PAIRS = 11

# Cropping coordinates for each value (relative to overlay)
PLAYER_NAME_X_START = 0
PLAYER_NAME_X_END = 150
PLAYER_NAME_Y_START = 0
PLAYER_NAME_Y_END = 32

LEVEL_X_START = 0
LEVEL_X_END = 25
LEVEL_Y_START = 34
LEVEL_Y_END = 56

GOLD_X_START = 35
GOLD_X_END = 75
GOLD_Y_START = 34
GOLD_Y_END = 56

HEALTH_X_START = 150
HEALTH_X_END = 202
HEALTH_Y_START = 18
HEALTH_Y_END = 48

class OverlayExtractor:
    def __init__(self, debug=False):
        self.debug = debug
        self.template_manager = PlayerTemplateManager()

    def extract_level_region(self, image, row_y):
        return image[row_y + LEVEL_Y_START:row_y + LEVEL_Y_END, OVERLAY_X + LEVEL_X_START:OVERLAY_X + LEVEL_X_END]

    def extract_gold_region(self, image, row_y):
        return image[row_y + GOLD_Y_START:row_y + GOLD_Y_END, OVERLAY_X + GOLD_X_START:OVERLAY_X + GOLD_X_END]

    def extract_health_region(self, image, row_y):
        return image[row_y + HEALTH_Y_START:row_y + HEALTH_Y_END, OVERLAY_X + HEALTH_X_START:OVERLAY_X + HEALTH_X_END]

    def extract_player_name_region(self, image, row_y):
        return image[row_y + PLAYER_NAME_Y_START:row_y + PLAYER_NAME_Y_END, OVERLAY_X + PLAYER_NAME_X_START:OVERLAY_X + PLAYER_NAME_X_END]

    def extract_row(self, image, row_y, row_num):
        # 1. Crop the full row region
        row_crop = image[row_y:row_y + ROW_HEIGHT, OVERLAY_X:OVERLAY_X + HEALTH_X_END]
        # 2. Convert to grayscale and binarize once
        row_gray = cv2.cvtColor(row_crop, cv2.COLOR_BGR2GRAY) if len(row_crop.shape) == 3 else row_crop
        _, row_bin = cv2.threshold(row_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3. Crop subregions from the binary row
        player_name_bin = row_bin[PLAYER_NAME_Y_START:PLAYER_NAME_Y_END, PLAYER_NAME_X_START:PLAYER_NAME_X_END]
        level_bin = row_bin[LEVEL_Y_START:LEVEL_Y_END, LEVEL_X_START:LEVEL_X_END]
        gold_bin = row_bin[GOLD_Y_START:GOLD_Y_END, GOLD_X_START:GOLD_X_END]
        health_bin = row_bin[HEALTH_Y_START:HEALTH_Y_END, HEALTH_X_START:HEALTH_X_END]
        # For debug/visualization, also crop original (non-binary) subregions
        player_name_crop = row_crop[PLAYER_NAME_Y_START:PLAYER_NAME_Y_END, PLAYER_NAME_X_START:PLAYER_NAME_X_END]
        level_crop = row_crop[LEVEL_Y_START:LEVEL_Y_END, LEVEL_X_START:LEVEL_X_END]
        gold_crop = row_crop[GOLD_Y_START:GOLD_Y_END, GOLD_X_START:GOLD_X_END]
        health_crop = row_crop[HEALTH_Y_START:HEALTH_Y_END, HEALTH_X_START:HEALTH_X_END]

        # Detect digits using shared_detector
        level_matches = shared_detector.find_all_digit_matches(level_bin, 'overlay', confidence_threshold=0.94)
        gold_matches = shared_detector.find_all_digit_matches(gold_bin, 'overlay', confidence_threshold=0.94)
        health_matches = shared_detector.find_all_digit_matches(health_bin, 'overlay_health', confidence_threshold=0.94)
        level_result = shared_detector.reconstruct_number_from_matches(level_matches)
        gold_result = shared_detector.reconstruct_number_from_matches(gold_matches)
        health_result = shared_detector.reconstruct_number_from_matches(health_matches)
        level = level_result['number'] if level_result else None
        gold = gold_result['number'] if gold_result else None
        health = health_result['number'] if health_result else None
        # Player name matching
        template_match = self.template_manager.find_player_by_template(player_name_bin)
        if template_match:
            player_name = template_match["player_name"]
        else:
            player_name = None
        return {
            'row': row_num,
            'player_name': player_name,
            'level': level,
            'gold': gold,
            'health': health,
            'player_name_binary': player_name_bin,
            'debug_crops': {
                'player_name': player_name_crop.copy(),
                'level': level_crop.copy(),
                'gold': gold_crop.copy(),
                'health': health_crop.copy()
            }
        }

def extract_overlay_from_image(image, config):
    extractor = OverlayExtractor(debug=getattr(config, 'debug', False))
    overlay_data = []
    debug_crops = []
    player_name_binaries = []
    # Calculate y-offsets for all 8 rows
    y_offsets = [OVERLAY_Y + i * ROW_HEIGHT for i in range(NUM_PLAYERS)]
    for row_num, row_y in enumerate(y_offsets):
        row_data = extractor.extract_row(image, row_y, row_num)
        overlay_data.append({
            'row': row_num,
            'player_name': row_data['player_name'],
            'level': row_data['level'],
            'gold': row_data['gold'],
            'health': row_data['health']
        })
        if row_data['player_name'] is None:
            player_name_binaries.append(row_data['player_name_binary'])
        else:
            player_name_binaries.append(None)
        debug_crops.append(row_data['debug_crops'])
    if extractor.debug:
        print("#create_debug_grid_crops(overlay_data, debug_crops), line 113, in overlay_extraction.py")
    return overlay_data, player_name_binaries

def create_debug_grid_crops(results, debug_crops):
    """Create a single grid window showing all players' cropped regions in a structured format."""
    import cv2
    import numpy as np
    # Define grid parameters
    cell_width = 120
    cell_height = 48
    margin = 10
    header_height = 30
    
    # Calculate grid dimensions
    num_players = len(results)
    num_cols = 4  # Player Name, Level, Gold, Health
    grid_width = num_cols * cell_width + (num_cols + 1) * margin
    grid_height = (num_players + 1) * cell_height + (num_players + 2) * margin  # +1 for header
    
    # Create blank grid image
    grid_image = np.ones((grid_height, grid_width, 3), dtype=np.uint8) * 240  # Light gray background
    
    # Add header
    headers = ['Player Name', 'Level', 'Gold', 'Health']
    for col, header in enumerate(headers):
        x = margin + col * (cell_width + margin)
        y = margin
        # Draw header background
        cv2.rectangle(grid_image, (x, y), (x + cell_width, y + header_height), (200, 200, 200), -1)
        # Add header text
        cv2.putText(grid_image, header, (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    
    # Add player data rows
    for row_idx, crops in enumerate(debug_crops):
        y = margin + header_height + margin + row_idx * (cell_height + margin)
        for col, key in enumerate(['player_name', 'level', 'gold', 'health']):
            x = margin + col * (cell_width + margin)
            crop = crops[key]
            # Resize crop to fit cell
            crop_resized = cv2.resize(crop, (cell_width - 4, cell_height - 4))
            # If grayscale, convert to BGR
            if len(crop_resized.shape) == 2:
                crop_resized = cv2.cvtColor(crop_resized, cv2.COLOR_GRAY2BGR)
            # Place in grid
            grid_image[y + 2:y + cell_height - 2, x + 2:x + cell_width - 2] = crop_resized
            # Optional: Draw border
            cv2.rectangle(grid_image, (x, y), (x + cell_width, y + cell_height), (180, 180, 180), 1)
    
    # Show the grid
    cv2.imshow('Overlay Cropped Regions Grid', grid_image)
    print("Showing overlay cropped regions grid. Press any key to continue...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    import sys
    try:
        from components.utils import AnalysisConfig
        config = AnalysisConfig(debug=True)
    except ImportError:
        class DummyConfig:
            debug = True
        config = DummyConfig()
    img_path = sys.argv[1] if len(sys.argv) > 1 else "screenshots/SS_Latest.png"
    img = cv2.imread(img_path)
    values, player_name_binaries = extract_overlay_from_image(img, config)
    for v in values:
        print(f"Row {v['row']}: Level={v['level']} Gold={v['gold']} Health={v['health']}") 