from utils import AnalysisConfig, get_row_boundaries, load_and_preprocess_image, get_header_positions
from components.player_extraction import extract_players_from_scoreboard
from components.health_extraction import extract_health_from_scoreboard
from components.record_extraction import extract_record_from_scoreboard
from components.networth_extraction import extract_networth_from_scoreboard
from components.crew_bench_extraction import extract_crew_and_bench_from_scoreboard

import time



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
    
    def print_summary(self, show_timing=False):
        if not show_timing:
            return
            
        total_time = self.get_total_time()
        print(f"\n=== PERFORMANCE TIMING ===")
        
        for phase, phase_time in self.times.items():
            percentage = (phase_time / total_time * 100) if total_time > 0 else 0
            print(f"{phase:<20} {phase_time:.3f}s ({percentage:.1f}%)")
        
        print(f"{'TOTAL TIME:':<20} {total_time:.3f}s")
        print("=" * 35)









def extract_all_players(image, thresh, header_positions, crew_results, bench_results, config, tracker=None):
    """Extract data for all players and combine into final structure."""
    if config.debug:
        print("\n=== EXTRACTING DATA ===")
        print(f"Detected columns: {list(header_positions.keys())}")
    
    # Extract player data using the new player extraction system
    if config.debug:
        print("\n=== PLAYER COLUMN DATA ===")
    players_data = extract_players_from_scoreboard(image, config)
    if tracker:
        tracker.mark("Player Extraction")
    
    if config.debug:
        print("\n=== HEALTH COLUMN DATA ===")
    health_data = extract_health_from_scoreboard(image, header_positions.get("HEALTH"), config)
    if tracker:
        tracker.mark("Health Extraction")
    
    if config.debug:
        print("\n=== RECORD COLUMN DATA ===")
    record_data = extract_record_from_scoreboard(image, header_positions.get("RECORD"), config)
    if tracker:
        tracker.mark("Record Extraction")
    
    if config.debug:
        print("\n=== NETWORTH COLUMN DATA ===")
    networth_data = extract_networth_from_scoreboard(image, header_positions.get("NETWORTH"), config)
    if tracker:
        tracker.mark("NetWorth Extraction")
    

    if config.debug:
        print(f"###########################################################################################"+" Summary of extracted data")

    # Combine player data with crew/bench results
    combined_players = []
    
    for player_data in players_data:
        row_num = player_data["playerRow"]

        # Skip players with no level and no gold
        if player_data["playerLevel"] is None and player_data["playerGold"] is None:
            if config.debug:
                print(f"Skipping player at row {row_num}: missing both level and gold")
            continue
        
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
        
        # Add crew information (already filtered in extraction)
        if row_num in crew_results:
            combined_player["crew"] = crew_results[row_num]
        
        # Add bench information (already filtered in extraction)
        if row_num in bench_results:
            combined_player["bench"] = bench_results[row_num]
        
        combined_players.append(combined_player)
    
    return combined_players

def main(config):
    #config = AnalysisConfig(debug=True, show_timing=True, show_visualization=False)
    tracker = PerformanceTracker()
    tracker.start()

    image_path = IMAGE_PATH
    image, thresh = load_and_preprocess_image(image_path, config)
    tracker.mark("Image Loading")
    
    if image is None:
        print("Failed to load image")
        return
    
    # Get header positions
    header_positions = get_header_positions(thresh)
    tracker.mark("Header Detection")
    if config.debug:
        print(f"Found headers: {list(header_positions.keys())}")
    
    # If no headers found, abort extraction
    if not header_positions:
        print("No headers found in the image. Extraction aborted.")
        return

    # Extract crew and bench data (heroes and star levels)
    crew_results, bench_results = extract_crew_and_bench_from_scoreboard(image, thresh, header_positions, config)
    tracker.mark("Crew/Bench Extraction")
    
    # Extract all player data and combine
    players = extract_all_players(image, thresh, header_positions, crew_results, bench_results, config, tracker)
    tracker.mark("Data Combination")
    
        # Create final scoreboard structure
    scoreboard_data = {
        "metadata": {
            "total_players": len(players),
            "headers_found": list(header_positions.keys()),
            "extraction_time": tracker.get_total_time(),
            "image_path": image_path,
            "timing_breakdown": dict(tracker.times),
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
    
    # Print timing summary if enabled
    tracker.print_summary(config.show_timing)
    
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

def print_metadata(scoreboard_data):
    """Print a clean overview of the extracted data structure."""
    print("\n=== METADATA ===")
    
    # Print metadata
    metadata = scoreboard_data["metadata"]
    print(f"   Metadata:")
    print(f"   Total players: {metadata['total_players']}")
    print(f"   Headers found: {metadata['headers_found']}")
    print(f"   Extraction time: {metadata['extraction_time']:.3f}s")
    print(f"   Players with names: {metadata['extraction_summary']['players_with_names']}")
    print(f"   Players with health: {metadata['extraction_summary']['players_with_health']}")
    print(f"   Players with record: {metadata['extraction_summary']['players_with_record']}")
    print(f"   Players with networth: {metadata['extraction_summary']['players_with_networth']}")
    print(f"   Total crew units: {metadata['extraction_summary']['total_crew_units']}")
    print(f"   Total bench units: {metadata['extraction_summary']['total_bench_units']}")

def print_scoreboard_data(scoreboard_data):
    """Print the scoreboard data in a readable format."""
    print("\n=== SCOREBOARD DATA ===")
    for i, player in enumerate(scoreboard_data["players"]):
        crew_heroes = [f"{unit.get('hero_name', 'Unknown')}({unit.get('star_level', 0)}⭐)" for unit in player['crew']]
        bench_heroes = [f"{unit.get('hero_name', 'Unknown')}({unit.get('star_level', 0)}⭐)" for unit in player['bench']]
        
        # Format extracted stats
        health = player.get('health', 'N/A')
        wins = player.get('wins', 'N/A')
        losses = player.get('losses', 'N/A')
        networth = player.get('networth', 'N/A')
        
        print(f"\033[1;37m   {i+1}. {player['player_name']}\033[0m (Level: \033[1;36m{player['level']}\033[0m, Gold: \033[1;33m{player['gold']}\033[0m, Health: \033[1;32m{health}\033[0m, Win: \033[1;35m{wins}\033[0m, Loss: \033[1;35m{losses}\033[0m, Networth: \033[1;31m{networth}\033[0m)")
        print(f"\033[1;34m      Crew:  \033[1;37m{crew_heroes}")
        print(f"\033[1;34m      Bench: \033[1;37m{bench_heroes}")
        print()
    
#IMAGE_PATH = "screenshots/SS_Latest.png"
IMAGE_PATH = "assets/templates/screenshots_for_templates/SS_18.png"
if __name__ == "__main__":
    config = AnalysisConfig(debug=True, show_timing=True, show_visualization=False)
    # Run the main extraction
    scoreboard_data = main(config)
    
    if scoreboard_data:
        # Save to JSON file
        save_scoreboard_data(scoreboard_data)
        
        # Print comprehensive data structure
        #print_metadata(scoreboard_data)
        #print()
        print_scoreboard_data(scoreboard_data)
    else:
        print("No data extracted")
