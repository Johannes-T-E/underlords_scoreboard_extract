import cv2
import numpy as np
import os

from components.utils import get_row_boundaries, AnalysisConfig, load_and_preprocess_image, get_header_positions
from components.shared_digit_detector import shared_detector

class HealthExtractor:
    """Extracts health values from scoreboard rows."""
    def __init__(self, debug=False):
        self.debug = debug

    def extract_health_region(self, image, row_y, health_column_x):
        health_width = 100  # Width of health display area
        health_height = 80  # Full row height
        health_y_start = row_y
        health_y_end = health_y_start + health_height
        health_x_start = health_column_x
        health_x_end = health_x_start + health_width
        health_region = image[health_y_start:health_y_end, health_x_start:health_x_end]
        return health_region

    def extract_health_value(self, image, row_y, health_column_x):
        health_region = self.extract_health_region(image, row_y, health_column_x)
        if health_region.size == 0:
            return 0
        digit_matches = shared_detector.find_all_digit_matches(health_region, 'health', confidence_threshold=0.95)
        if digit_matches:
            number_result = shared_detector.reconstruct_number_from_matches(digit_matches)
            if number_result and 0 <= number_result['number'] <= 100:
                if self.debug:
                    print(f"Found health: {number_result['number']} (confidence: {number_result['confidence']:.3f}, digits: {number_result['digit_count']})")
                return number_result['number']
        return 0

def extract_health_from_scoreboard(image, health_column_x, config):
    """Extract health data for all rows in the scoreboard."""
    if config.debug:
        print(f"########################################################################################### health_extraction.py - STARTED ")
        health_templates = shared_detector.get_digit_templates('health')
        print(f"Health templates loaded: {len(health_templates)} templates")
        if health_templates:
            print(f"Available health digits: {list(health_templates.keys())}")
    if health_column_x is None:
        if config.debug:
            print("Health column not detected, returning empty data")
        return []
    extractor = HealthExtractor(debug=config.debug)
    health_data = []
    row_boundaries = get_row_boundaries()
    for row_num, row_y in enumerate(row_boundaries):
        if config.debug:
            print(f"\n--- Extracting Health for Row {row_num} ---")
        health_value = extractor.extract_health_value(image, row_y, health_column_x)
        health_data.append({
            "row": row_num,
            "health": health_value
        })
        if config.debug:
            print(f"Row {row_num}: Health = {health_value}")
    if config.debug:
        print(f"########################################################################################### health_extraction.py - FINISHED")
    return health_data

if __name__ == "__main__":
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_14.png"
    image, thresh = load_and_preprocess_image(image_path, config)
    if image is not None:
        header_positions = get_header_positions(thresh)
        health_column_x = header_positions.get("HEALTH")
        if health_column_x:
            print(f"Health column found at x={health_column_x}")
            health_data = extract_health_from_scoreboard(image, health_column_x, config)
            print(f"\n=== EXTRACTED HEALTH DATA ===")
            for row_data in health_data:
                print(f"Row {row_data['row']}: Health = {row_data['health']}")
        else:
            print("HEALTH column not found in header positions")
    else:
        print(f"Failed to load image: {image_path}") 