import sys
import json
from components.calculate_hero_slots import calculate_hero_slots, calculate_crew_slots, calculate_bench_slots
from components.image_processing import find_column_headers, find_column_headers_fast, find_column_headers_with_timing, create_all_slots_masks, load_template_masks, analyze_all_masks
from utils import AnalysisConfig, get_row_boundaries, load_and_preprocess_image, get_header_positions
from player_extraction import extract_players_from_scoreboard
from health_extraction import extract_health_from_scoreboard
from record_extraction import extract_record_from_scoreboard
from networth_extraction import extract_networth_from_scoreboard
import cv2
import os
import glob
import time
import re



class PerformanceTracker:
    """Tracks performance metrics for different phases."""
    def __init__(self):
        self.times = {}
        self.start_time = None
        self.last_mark_time = None
    
    def start(self):
        self.start_time = time.time()
        self.last_mark_time = self.start_time
    
    def mark(self, phase_name):
        if self.start_time is None:
            self.start_time = time.time()
            self.last_mark_time = self.start_time
        
        current_time = time.time()
        # Store the time for this specific phase (not cumulative)
        self.times[phase_name] = current_time - self.last_mark_time
        self.last_mark_time = current_time
    
    def get_total_time(self):
        return time.time() - self.start_time if self.start_time else 0
    
    def print_summary(self, method_used):
        total_time = self.get_total_time()
        print(f"\n=== PERFORMANCE SUMMARY ===")
        print(f"Method used: {method_used.upper()}")
        
        for phase, phase_time in self.times.items():
            percentage = (phase_time / total_time * 100) if total_time > 0 else 0
            print(f"{phase:<18} {phase_time:.3f}s ({percentage:.1f}%)")
        
        print(f"TOTAL TIME:        {total_time:.3f}s")







def calculate_slots(crew_start_x, crew_end_x, bench_start_x, image_width, config):
    """Calculate slot positions for crew and bench."""
    if config.debug:
        print("\nCalculating slot positions...")
    
    row_boundaries = get_row_boundaries()
    crew_slots_by_row = {}
    bench_slots_by_row = {}
    
    for row_num, row_boundary in enumerate(row_boundaries):
        if crew_start_x is not None and crew_end_x is not None:
            crew_slots = calculate_crew_slots(crew_start_x, crew_end_x, row_boundary)
            crew_slots_by_row[row_num] = crew_slots
        
        if bench_start_x is not None:
            bench_slots = calculate_bench_slots(bench_start_x, image_width, row_boundary)
            bench_slots_by_row[row_num] = bench_slots
    
    if config.debug:
        print(f"Crew slots by row: {[(row, len(slots)) for row, slots in crew_slots_by_row.items()]}")
        print(f"Bench slots by row: {[(row, len(slots)) for row, slots in bench_slots_by_row.items()]}")
    
    return crew_slots_by_row, bench_slots_by_row

def create_slot_masks(image, crew_slots_by_row, bench_slots_by_row, config):
    """Create masks for all slots."""
    if config.debug:
        print("\nCreating slot masks...")
    
    crew_masks_by_row, bench_masks_by_row = create_all_slots_masks(image, crew_slots_by_row, bench_slots_by_row)
    
    if config.debug:
        for row_num in crew_masks_by_row:
            crew_masks = crew_masks_by_row[row_num]
            print(f"Row {row_num}: {len(crew_masks)} crew masks created")
        
        for row_num in bench_masks_by_row:
            bench_masks = bench_masks_by_row[row_num]
            print(f"Row {row_num}: {len(bench_masks)} bench masks created")
    
    return crew_masks_by_row, bench_masks_by_row

def analyze_heroes(crew_masks_by_row, bench_masks_by_row, config):
    """Analyze masks for hero identification."""
    if config.debug:
        print("\n=== LOADING TEMPLATE MASKS ===")
    
    template_masks = load_template_masks("assets/templates/hero_templates/masks", debug=config.debug)
    
    if config.debug:
        print("\n=== ANALYZING MASKS FOR HERO IDENTIFICATION ===")
    
    crew_results, bench_results = analyze_all_masks(crew_masks_by_row, bench_masks_by_row, template_masks, debug=config.debug)
    
    return crew_results, bench_results


####################### boilerplate code #######################

def extract_text_from_region(thresh, x_start, y_start, width, height):
    """Extract text from a specific region using OCR."""
    try:
        import pytesseract
        roi = thresh[y_start:y_start+height, x_start:x_start+width]
        text = pytesseract.image_to_string(roi, config='--oem 3 --psm 8').strip()
        return text
    except:
        return ""

def extract_number_from_region(thresh, x_start, y_start, width, height):
    """Extract number from a specific region using OCR."""
    try:
        import pytesseract
        roi = thresh[y_start:y_start+height, x_start:x_start+width]
        text = pytesseract.image_to_string(roi, config='--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789').strip()
        return int(text) if text.isdigit() else 0
    except:
        return 0

def parse_record(record_text):
    """Parse win/loss record from text like '5-3' or '5W-3L'."""
    if not record_text:
        return {"wins": 0, "losses": 0}
    
    # Handle formats like "5-3", "5W-3L", "5 - 3", etc.
    match = re.search(r'(\d+).*?(\d+)', record_text)
    if match:
        return {"wins": int(match.group(1)), "losses": int(match.group(2))}
    
    return {"wins": 0, "losses": 0}

################################################################

def detect_star_level(thresh, x_center, y_bottom, slot_width=56, star_area_height=18):
    """Detect star level by counting white pixels in the star area below hero icon."""
    # Calculate star area coordinates
    x_start = x_center - slot_width // 2
    x_end = x_start + slot_width
    y_start = y_bottom
    y_end = y_start + star_area_height
    
    # Extract star area from binary image
    star_area = thresh[y_start:y_end, x_start:x_end]
    
    # Count white pixels (value 255 in binary image)
    white_pixel_count = cv2.countNonZero(star_area)
    total_pixels = star_area.shape[0] * star_area.shape[1]
    
    # Calculate white pixel percentage
    white_percentage = (white_pixel_count / total_pixels) * 100 if total_pixels > 0 else 0
    
    # Determine star level based on white pixel percentage
    # These thresholds may need adjustment based on your specific images
    if white_percentage >= 40:
        return 3  # 3 stars
    elif white_percentage >= 20:
        return 2  # 2 stars
    elif white_percentage >= 1:
        return 1  # 1 star
    else:
        return 0  # No stars (empty slot)

def add_star_levels_to_results(thresh, crew_results, bench_results, crew_slots_by_row, bench_slots_by_row, config):
    """Add star level information to hero analysis results."""
    
    # Process crew slots
    for row_num, crew_slots in crew_slots_by_row.items():
        if row_num in crew_results:
            for i, slot in enumerate(crew_slots):
                if i < len(crew_results[row_num]):
                    star_level = detect_star_level(thresh, slot['x_center'], slot['y_end'])
                    crew_results[row_num][i]['star_level'] = star_level
                    
                    if config.debug:
                        hero_name = crew_results[row_num][i].get('hero_name', 'Unknown')
                        print(f"Row {row_num}, Crew slot {i}: {hero_name} - {star_level} stars")
    
    # Process bench slots
    for row_num, bench_slots in bench_slots_by_row.items():
        if row_num in bench_results:
            for i, slot in enumerate(bench_slots):
                if i < len(bench_results[row_num]):
                    star_level = detect_star_level(thresh, slot['x_center'], slot['y_end'])
                    bench_results[row_num][i]['star_level'] = star_level
                    
                    if config.debug:
                        hero_name = bench_results[row_num][i].get('hero_name', 'Unknown')
                        print(f"Row {row_num}, Bench slot {i}: {hero_name} - {star_level} stars")
    
    return crew_results, bench_results

def is_filled_slot(slot):
    """Check if a slot contains a valid hero."""
    if not slot:
        return False
    
    hero_name = slot.get('hero_name', '')
    confidence = slot.get('confidence', 0)
    
    # Filter out empty indicators
    if not hero_name or hero_name in ['Unknown', 'Empty', 'None', '']:
        return False
    
    # Filter out very low confidence matches (likely empty slots)
    if confidence < 0.5:
        return False
    
    return True

def extract_all_players(image, thresh, header_positions, crew_results, bench_results, config):
    """Extract data for all players and combine into final structure."""
    
    # Extract player data using the new player extraction system
    if config.debug:
        print("\n=== EXTRACTING PLAYER DATA ===")
    
    players_data = extract_players_from_scoreboard(image, header_positions, config)
    
    # Extract additional player data (health, record, networth)
    if config.debug:
        print("\n=== EXTRACTING ADDITIONAL PLAYER DATA ===")
        print(f"Detected columns: {list(header_positions.keys())}")
    
    health_data = extract_health_from_scoreboard(image, header_positions.get("HEALTH"), config)
    record_data = extract_record_from_scoreboard(image, header_positions.get("RECORD"), config)
    networth_data = extract_networth_from_scoreboard(image, header_positions.get("NETWORTH"), config)
    
    if config.debug:
        print(f"Health data rows: {len(health_data)}")
        print(f"Record data rows: {len(record_data)}")
        print(f"NetWorth data rows: {len(networth_data)}")
    
    # Combine player data with crew/bench results
    combined_players = []
    
    for player_data in players_data:
        row_num = player_data["playerRow"]
        
        # Get corresponding data from other extraction functions (with safe defaults)
        health_info = next((h for h in health_data if h["row"] == row_num), {"health": None})
        record_info = next((r for r in record_data if r["row"] == row_num), {"wins": None, "losses": None})
        networth_info = next((n for n in networth_data if n["row"] == row_num), {"networth": None})
        
        if config.debug:
            missing_columns = []
            if health_info["health"] is None and "HEALTH" not in header_positions:
                missing_columns.append("HEALTH")
            if record_info["wins"] is None and "RECORD" not in header_positions:
                missing_columns.append("RECORD")
            if networth_info["networth"] is None and "NETWORTH" not in header_positions:
                missing_columns.append("NETWORTH")
            
            if missing_columns:
                print(f"Row {row_num}: Missing columns {missing_columns}, using default values")
        
        # Create combined player structure
        combined_player = {
            # Basic player info
            "row_number": row_num,
            "position": row_num + 1,  # Leaderboard position (1-8)
            "player_name": player_data["playerName"],
            
            # Player stats (extracted)
            "level": player_data["playerLevel"],
            "gold": player_data["playerGold"],
            
            # Player stats (extracted from additional data)
            "health": health_info.get("health"),
            "wins": record_info.get("wins"),
            "losses": record_info.get("losses"),
            "networth": networth_info.get("networth"),
            
            # Game units and alliances
            "crew": [],
            "bench": [],
            "alliances": [],  # To be calculated from crew
            
            # Special units (future implementation)
            "underlord": None,     # To be extracted
            "contraption": None    # To be extracted
        }
        
        # Add crew information
        if row_num in crew_results:
            # Filter out empty slots using comprehensive check
            filled_crew = [slot for slot in crew_results[row_num] if is_filled_slot(slot)]
            combined_player["crew"] = filled_crew
        
        # Add bench information
        if row_num in bench_results:
            # Filter out empty slots using comprehensive check
            filled_bench = [slot for slot in bench_results[row_num] if is_filled_slot(slot)]
            combined_player["bench"] = filled_bench
        
        combined_players.append(combined_player)
        
        if config.debug:
            crew_count = len(combined_player["crew"])
            bench_count = len(combined_player["bench"])
            health = combined_player.get("health", "N/A")
            wins = combined_player.get("wins", "N/A")
            losses = combined_player.get("losses", "N/A")
            networth = combined_player.get("networth", "N/A")
            print(f"Row {row_num}: {player_data['playerName']} (L{player_data['playerLevel']}, G{player_data['playerGold']}, H{health}, W{wins}-L{losses}, NW{networth}) - {crew_count} crew, {bench_count} bench")
    
    return combined_players

def main():
    config = AnalysisConfig(debug=True, show_timing=True, show_visualization=True)
    tracker = PerformanceTracker()
    tracker.start()

    image_path = "assets/templates/screenshots_for_templates/SS_08.png"
    image, thresh = load_and_preprocess_image(image_path, config)
    
    if image is None:
        print("Failed to load image")
        return
    
    # Get header positions
    header_positions = get_header_positions(thresh)
    print(f"Found headers: {list(header_positions.keys())}")
    
    # Extract hero and bench information
    crew_start_x = header_positions.get("CREW")
    crew_end_x = header_positions.get("UNDERLORD")
    bench_start_x = header_positions.get("BENCH")

    crew_slots_by_row, bench_slots_by_row = calculate_slots(crew_start_x, crew_end_x, bench_start_x, image.shape[1], config)
    crew_masks_by_row, bench_masks_by_row = create_slot_masks(image, crew_slots_by_row, bench_slots_by_row, config)
    crew_results, bench_results = analyze_heroes(crew_masks_by_row, bench_masks_by_row, config)
    
    # Add star level detection to hero results
    if config.debug:
        print("\n=== DETECTING STAR LEVELS ===")
    crew_results, bench_results = add_star_levels_to_results(thresh, crew_results, bench_results, crew_slots_by_row, bench_slots_by_row, config)
    
    # Extract all player data and combine
    players = extract_all_players(image, thresh, header_positions, crew_results, bench_results, config)
    
    # Create final scoreboard structure
    scoreboard_data = {
        "metadata": {
            "total_players": len(players),
            "headers_found": list(header_positions.keys()),
            "extraction_time": tracker.get_total_time(),
            "image_path": image_path,
            "extraction_summary": {
                "players_with_names": sum(1 for p in players if p["player_name"]),
                "players_with_health": sum(1 for p in players if p["health"] is not None),
                "players_with_record": sum(1 for p in players if p["wins"] is not None and p["losses"] is not None),
                "players_with_networth": sum(1 for p in players if p["networth"] is not None),
                "total_crew_units": sum(len(p["crew"]) for p in players),
                "total_bench_units": sum(len(p["bench"]) for p in players)
            }
        },
        "players": players
    }
    
    # Print summary
    if config.debug:
        print("\n=== EXTRACTION SUMMARY ===")
        print(f"Total players: {scoreboard_data['metadata']['total_players']}")
        print(f"Players with names: {scoreboard_data['metadata']['extraction_summary']['players_with_names']}")
        print(f"Players with health: {scoreboard_data['metadata']['extraction_summary']['players_with_health']}")
        print(f"Players with record: {scoreboard_data['metadata']['extraction_summary']['players_with_record']}")
        print(f"Players with networth: {scoreboard_data['metadata']['extraction_summary']['players_with_networth']}")
        print(f"Total crew units: {scoreboard_data['metadata']['extraction_summary']['total_crew_units']}")
        print(f"Total bench units: {scoreboard_data['metadata']['extraction_summary']['total_bench_units']}")
        print(f"Extraction time: {scoreboard_data['metadata']['extraction_time']:.3f}s")
    
    return scoreboard_data
def save_scoreboard_data(scoreboard_data, output_path="output/scoreboard_data.json"):
    """Save the extracted scoreboard data to a JSON file."""
    import json
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(scoreboard_data, f, indent=2, ensure_ascii=False)
    
    print(f"Scoreboard data saved to: {output_path}")

def print_json_structure(scoreboard_data):
    """Print a clean overview of the extracted data structure."""
    print("\n=== EXTRACTED JSON STRUCTURE ===")
    
    # Print metadata
    metadata = scoreboard_data["metadata"]
    print(f"📊 Metadata:")
    print(f"   Total players: {metadata['total_players']}")
    print(f"   Headers found: {metadata['headers_found']}")
    print(f"   Extraction time: {metadata['extraction_time']:.3f}s")
    print(f"   Players with names: {metadata['extraction_summary']['players_with_names']}")
    print(f"   Players with health: {metadata['extraction_summary']['players_with_health']}")
    print(f"   Players with record: {metadata['extraction_summary']['players_with_record']}")
    print(f"   Players with networth: {metadata['extraction_summary']['players_with_networth']}")
    print(f"   Total crew units: {metadata['extraction_summary']['total_crew_units']}")
    print(f"   Total bench units: {metadata['extraction_summary']['total_bench_units']}")
    
    # Print player data
    print(f"\n👥 Players:")
    for i, player in enumerate(scoreboard_data["players"]):
        crew_heroes = [f"{unit.get('hero_name', 'Unknown')}({unit.get('star_level', 0)}⭐)" for unit in player['crew']]
        bench_heroes = [f"{unit.get('hero_name', 'Unknown')}({unit.get('star_level', 0)}⭐)" for unit in player['bench']]
        
        # Format extracted stats
        health = player.get('health', 'N/A')
        wins = player.get('wins', 'N/A')
        losses = player.get('losses', 'N/A')
        networth = player.get('networth', 'N/A')
        
        print(f"   {i+1}. {player['player_name']} (L{player['level']}, G{player['gold']}, H{health}, W{wins}-L{losses}, NW{networth})")
        print(f"      Crew: {crew_heroes}")
        print(f"      Bench: {bench_heroes}")
        
        # Show future fields status (only remaining unimplemented fields)
        future_fields = ["underlord", "contraption"]
        implemented = [f for f in future_fields if player.get(f) is not None]
        if implemented:
            print(f"      Future fields: {implemented}")
        print()

if __name__ == "__main__":
    # Run the main extraction
    scoreboard_data = main()
    
    if scoreboard_data:
        # Save to JSON file
        save_scoreboard_data(scoreboard_data)
        
        # Print comprehensive data structure
        print_json_structure(scoreboard_data)
    else:
        print("No data extracted")
