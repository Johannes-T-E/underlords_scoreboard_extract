import cv2
import numpy as np
import os
import sys

from components.utils import get_row_boundaries, AnalysisConfig, load_and_preprocess_image, get_header_positions
from components.shared_digit_detector import shared_detector

class RecordExtractor:
    """Extracts record values from scoreboard rows."""
    def __init__(self, debug=False):
        self.debug = debug

    def extract_record_region(self, image, row_y, record_column_x):
        record_width = 100  # Width of record display area
        record_height = 80  # Full row height
        record_y_start = row_y
        record_y_end = record_y_start + record_height
        record_x_start = record_column_x
        record_x_end = record_x_start + record_width
        record_region = image[record_y_start:record_y_end, record_x_start:record_x_end]
        return record_region

    def extract_record_value(self, image, row_y, record_column_x):
        record_region = self.extract_record_region(image, row_y, record_column_x)
        if record_region.size == 0:
            return {"wins": 0, "losses": 0}
        matches = shared_detector.find_digits_and_separator(record_region)
        if matches:
            record_result = shared_detector.reconstruct_record_from_matches(matches)
            if record_result:
                if self.debug:
                    print(f"Found record: {record_result['wins']}-{record_result['losses']} (confidence: {record_result['confidence']:.3f}, matches: {record_result['total_matches']})")
                return {"wins": record_result['wins'], "losses": record_result['losses']}
        return {"wins": 0, "losses": 0}

def extract_record_from_scoreboard(image, record_column_x, config):
    """Extract record data for all rows in the scoreboard."""
    if config.debug:
        print(f"########################################################################################### record_extraction.py - STARTED ")
        record_templates = shared_detector.get_digit_templates('record')
        separator_template = shared_detector.get_separator_template()
        print(f"Record templates loaded: {len(record_templates)} digits, separator: {separator_template is not None}")
        if record_templates:
            print(f"Available record digits: {list(record_templates.keys())}")
    if record_column_x is None:
        if config.debug:
            print("Record column not detected, returning empty data")
        return []
    extractor = RecordExtractor(debug=config.debug)
    record_data = []
    row_boundaries = get_row_boundaries()
    for row_num, row_y in enumerate(row_boundaries):
        if config.debug:
            print(f"\n--- Extracting Record for Row {row_num} ---")
        record_value = extractor.extract_record_value(image, row_y, record_column_x)
        record_data.append({
            "row": row_num,
            "wins": record_value["wins"],
            "losses": record_value["losses"]
        })
        if config.debug:
            print(f"Row {row_num}: Record = {record_value['wins']}-{record_value['losses']}")
    if config.debug:
        print(f"########################################################################################### record_extraction.py - FINISHED")
    return record_data

if __name__ == "__main__":
    config = AnalysisConfig(debug=True)
    image_path = "assets/templates/screenshots_for_templates/SS_14.png"
    image, thresh = load_and_preprocess_image(image_path, config)
    if image is not None:
        header_positions = get_header_positions(thresh)
        record_column_x = header_positions.get("RECORD")
        if record_column_x:
            print(f"Record column found at x={record_column_x}")
            record_data = extract_record_from_scoreboard(image, record_column_x, config)
            print(f"\n=== EXTRACTED RECORD DATA ===")
            for row_data in record_data:
                print(f"Row {row_data['row']}: Record = {row_data['wins']}-{row_data['losses']}")
        else:
            print("RECORD column not found in header positions")
    else:
        print(f"Failed to load image: {image_path}") 