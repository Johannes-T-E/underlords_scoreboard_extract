import cv2
import numpy as np
import os
from components.utils import get_row_boundaries, AnalysisConfig, load_and_preprocess_image, get_header_positions

class AdditionalDataExtractor:
    """Extracts health, record, and net worth areas from screenshots for template creation."""
    
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
    
    def extract_health_region(self, image, row_y, health_column_x):
        """Extract the health region from a specific row."""
        # Health region dimensions (typically 2-3 digits, e.g., "100", "45")
        health_width = 100  # Width of health display area
        health_height = 80  # Full row height
        
        # Calculate health region coordinates
        health_y_start = row_y
        health_y_end = health_y_start + health_height
        health_x_start = health_column_x
        health_x_end = health_x_start + health_width
        
        # Extract health region
        health_region = image[health_y_start:health_y_end, health_x_start:health_x_end]
        
        return health_region
    
    def extract_record_region(self, image, row_y, record_column_x):
        """Extract the record (wins-losses) region from a specific row."""
        # Record region dimensions (typically "X-Y" format, e.g., "5-3", "10-2")
        record_width = 100  # Width of record display area (e.g., "5-3")
        record_height = 80  # Full row height
        
        # Calculate record region coordinates
        record_y_start = row_y
        record_y_end = record_y_start + record_height
        record_x_start = record_column_x
        record_x_end = record_x_start + record_width
        
        # Extract record region
        record_region = image[record_y_start:record_y_end, record_x_start:record_x_end]
        
        return record_region
    
    def extract_networth_region(self, image, row_y, networth_column_x):
        """Extract the net worth region from a specific row."""
        # Net worth region dimensions (typically 2-4 digits, e.g., "50", "1250")
        networth_width = 100  # Width of net worth display area
        networth_height = 80  # Full row height
        
        # Calculate net worth region coordinates
        networth_y_start = row_y
        networth_y_end = networth_y_start + networth_height
        networth_x_start = networth_column_x
        networth_x_end = networth_x_start + networth_width
        
        # Extract net worth region
        networth_region = image[networth_y_start:networth_y_end, networth_x_start:networth_x_end]
        
        return networth_region
    
    def extract_all_health_areas(self, image, health_column_x, output_dir="assets/health_areas_to_crop"):
        """Extract and save all health areas from all players for manual cropping."""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get row boundaries
        row_boundaries = get_row_boundaries()
        
        saved_count = 0
        
        for row_num, row_y in enumerate(row_boundaries):
            # Extract health region for this row
            health_region = self.extract_health_region(image, row_y, health_column_x)
            
            if health_region.size > 0:
                # Convert to binary for consistency with template matching
                health_region_binary = self._convert_to_binary(health_region)
                
                # Save the binary health region as an image
                output_path = os.path.join(output_dir, f"health_area_row_{row_num}.png")
                cv2.imwrite(output_path, health_region_binary)
                saved_count += 1
                
                if self.debug:
                    print(f"Saved binary health area for row {row_num}: {output_path}")
        
        print(f"Extracted {saved_count} binary health areas to {output_dir}")
        return saved_count
    
    def extract_all_record_areas(self, image, record_column_x, output_dir="assets/record_areas_to_crop"):
        """Extract and save all record areas from all players for manual cropping."""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get row boundaries
        row_boundaries = get_row_boundaries()
        
        saved_count = 0
        
        for row_num, row_y in enumerate(row_boundaries):
            # Extract record region for this row
            record_region = self.extract_record_region(image, row_y, record_column_x)
            
            if record_region.size > 0:
                # Convert to binary for consistency with template matching
                record_region_binary = self._convert_to_binary(record_region)
                
                # Save the binary record region as an image
                output_path = os.path.join(output_dir, f"record_area_row_{row_num}.png")
                cv2.imwrite(output_path, record_region_binary)
                saved_count += 1
                
                if self.debug:
                    print(f"Saved binary record area for row {row_num}: {output_path}")
        
        print(f"Extracted {saved_count} binary record areas to {output_dir}")
        return saved_count
    
    def extract_all_networth_areas(self, image, networth_column_x, output_dir="assets/networth_areas_to_crop"):
        """Extract and save all net worth areas from all players for manual cropping."""
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Get row boundaries
        row_boundaries = get_row_boundaries()
        
        saved_count = 0
        
        for row_num, row_y in enumerate(row_boundaries):
            # Extract net worth region for this row
            networth_region = self.extract_networth_region(image, row_y, networth_column_x)
            
            if networth_region.size > 0:
                # Convert to binary for consistency with template matching
                networth_region_binary = self._convert_to_binary(networth_region)
                
                # Save the binary net worth region as an image
                output_path = os.path.join(output_dir, f"networth_area_row_{row_num}.png")
                cv2.imwrite(output_path, networth_region_binary)
                saved_count += 1
                
                if self.debug:
                    print(f"Saved binary net worth area for row {row_num}: {output_path}")
        
        print(f"Extracted {saved_count} binary net worth areas to {output_dir}")
        return saved_count
    
    def extract_all_additional_data_areas(self, image, header_positions):
        """Extract all additional data areas (health, record, net worth) from a screenshot."""
        # Get column positions from header positions (using exact names from templates)
        health_column_x = header_positions.get("HEALTH")
        record_column_x = header_positions.get("RECORD") 
        networth_column_x = header_positions.get("NETWORTH")
        
        total_extracted = 0
        
        # Extract health areas if column found
        if health_column_x:
            print("\n=== EXTRACTING HEALTH AREAS ===")
            health_count = self.extract_all_health_areas(image, health_column_x)
            total_extracted += health_count
            print("You can now manually crop these images to create health digit templates:")
            print("1. Open each image in paint")
            print("2. Crop to show only individual digits")
            print("3. Save as assets/templates/digits_health/digit_X.png (where X is the digit)")
        else:
            print("HEALTH column not found in header positions")
        
        # Extract record areas if column found
        if record_column_x:
            print("\n=== EXTRACTING RECORD AREAS ===")
            record_count = self.extract_all_record_areas(image, record_column_x)
            total_extracted += record_count
            print("You can now manually crop these images to create record digit templates:")
            print("1. Open each image in paint")
            print("2. Crop to show individual digits and dash symbol")
            print("3. Save as assets/templates/digits_record/digit_X.png or dash.png")
        else:
            print("RECORD column not found in header positions")
        
        # Extract net worth areas if column found
        if networth_column_x:
            print("\n=== EXTRACTING NET WORTH AREAS ===")
            networth_count = self.extract_all_networth_areas(image, networth_column_x)
            total_extracted += networth_count
            print("You can now manually crop these images to create net worth digit templates:")
            print("1. Open each image in paint")
            print("2. Crop to show only individual digits")
            print("3. Save as assets/templates/digits_networth/digit_X.png (where X is the digit)")
        else:
            print("NETWORTH column not found in header positions")
        
        return total_extracted

def extract_additional_data_areas_from_screenshot(image_path):
    """Extract health, record, and net worth areas from a screenshot for manual template creation."""
    config = AnalysisConfig(debug=True)
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is not None:
        # Get header positions using the same method as main.py
        header_positions = get_header_positions(thresh)
        print(f"Found headers: {list(header_positions.keys())}")
        
        # Show detected positions for debugging
        if config.debug:
            print(f"Header positions detected:")
            for header, pos in header_positions.items():
                print(f"  {header}: x={pos}")
        
        # Extract additional data areas
        extractor = AdditionalDataExtractor(debug=config.debug)
        total_count = extractor.extract_all_additional_data_areas(image, header_positions)
        
        print(f"\n=== EXTRACTION COMPLETE ===")
        print(f"Total areas extracted: {total_count}")
        print("Check the following folders for extracted areas:")
        print("- assets/health_areas_to_crop/")
        print("- assets/record_areas_to_crop/")
        print("- assets/networth_areas_to_crop/")
        
        return total_count
    else:
        print(f"Failed to load image: {image_path}")
        return 0

if __name__ == "__main__":
    # Extract additional data areas for template creation
    print("=== EXTRACTING ADDITIONAL DATA AREAS FOR TEMPLATES ===")
    image_path = "assets/templates/screenshots_for_templates/SS_14.png"
    count = extract_additional_data_areas_from_screenshot(image_path)
    print(f"Extracted {count} total areas. Check the respective folders for processing.") 