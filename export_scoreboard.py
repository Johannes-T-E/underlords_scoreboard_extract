import json
from datetime import datetime
from main import main

def export_scoreboard_to_json(scoreboard_data, output_file=None):
    """Export scoreboard data to JSON file."""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"scoreboard_data_{timestamp}.json"
    
    # Add extraction timestamp
    scoreboard_data["metadata"]["extracted_at"] = datetime.now().isoformat()
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(scoreboard_data, f, indent=2, ensure_ascii=False)
    
    print(f"Scoreboard data exported to: {output_file}")
    return output_file

def create_summary_report(scoreboard_data):
    """Create a summary report of the extracted data."""
    players = scoreboard_data["players"]
    
    report = {
        "total_players": len(players),
        "extraction_summary": {
            "players_with_names": sum(1 for p in players if p["player_name"]),
            "players_with_crew": sum(1 for p in players if p["crew"]),
            "players_with_bench": sum(1 for p in players if p["bench"]),
            "total_crew_units": sum(len(p["crew"]) for p in players),
            "total_bench_units": sum(len(p["bench"]) for p in players),
            "star_level_stats": {
                "crew_3_stars": sum(1 for p in players for unit in p["crew"] if unit.get('star_level', 0) == 3),
                "crew_2_stars": sum(1 for p in players for unit in p["crew"] if unit.get('star_level', 0) == 2),
                "crew_1_stars": sum(1 for p in players for unit in p["crew"] if unit.get('star_level', 0) == 1),
                "bench_3_stars": sum(1 for p in players for unit in p["bench"] if unit.get('star_level', 0) == 3),
                "bench_2_stars": sum(1 for p in players for unit in p["bench"] if unit.get('star_level', 0) == 2),
                "bench_1_stars": sum(1 for p in players for unit in p["bench"] if unit.get('star_level', 0) == 1),
            }
        },
        "player_summary": []
    }
    
    for i, player in enumerate(players):
        player_summary = {
            "position": i + 1,
            "name": player["player_name"] or f"Player {i+1}",
            "health": player["health"],
            "record": f"{player['record']['wins']}W-{player['record']['losses']}L",
            "networth": player["networth"],
            "crew_count": len(player["crew"]),
            "bench_count": len(player["bench"]),
            "alliances": player["alliances"],
            "crew_details": [{"name": unit.get('hero_name', 'Unknown'), "stars": unit.get('star_level', 0)} for unit in player["crew"]],
            "bench_details": [{"name": unit.get('hero_name', 'Unknown'), "stars": unit.get('star_level', 0)} for unit in player["bench"]]
        }
        report["player_summary"].append(player_summary)
    
    return report

if __name__ == "__main__":
    print("Extracting scoreboard data...")
    scoreboard_data = main()
    
    if scoreboard_data:
        # Export to JSON
        json_file = export_scoreboard_to_json(scoreboard_data)
        
        # Create summary report
        summary = create_summary_report(scoreboard_data)
        
        print("\n=== EXTRACTION SUMMARY ===")
        print(f"Total players: {summary['total_players']}")
        print(f"Players with names: {summary['extraction_summary']['players_with_names']}")
        print(f"Players with crew: {summary['extraction_summary']['players_with_crew']}")
        print(f"Players with bench: {summary['extraction_summary']['players_with_bench']}")
        print(f"Total crew units: {summary['extraction_summary']['total_crew_units']}")
        print(f"Total bench units: {summary['extraction_summary']['total_bench_units']}")
        
        # Print star level statistics
        star_stats = summary['extraction_summary']['star_level_stats']
        print(f"\n=== STAR LEVEL STATISTICS ===")
        print(f"Crew - 3★: {star_stats['crew_3_stars']}, 2★: {star_stats['crew_2_stars']}, 1★: {star_stats['crew_1_stars']}")
        print(f"Bench - 3★: {star_stats['bench_3_stars']}, 2★: {star_stats['bench_2_stars']}, 1★: {star_stats['bench_1_stars']}")
        
        # Export summary as well
        summary_file = json_file.replace(".json", "_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"Summary report exported to: {summary_file}")
    else:
        print("Failed to extract scoreboard data") 