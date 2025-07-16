import json
import os

RAW_SCOREBOARD_PATH = "output/scoreboard_data_raw.json"
OVERLAY_PATH = "output/overlay_data.json"
OUTPUT_PATH = "output/scoreboard_data.json"

def merge_scoreboard_and_overlay():
    if not os.path.exists(RAW_SCOREBOARD_PATH):
        print(f"Raw scoreboard data not found: {RAW_SCOREBOARD_PATH}")
        return
    if not os.path.exists(OVERLAY_PATH):
        print(f"Overlay data not found: {OVERLAY_PATH}")
        return
    with open(RAW_SCOREBOARD_PATH, "r", encoding="utf-8") as f:
        scoreboard = json.load(f)
    with open(OVERLAY_PATH, "r", encoding="utf-8") as f:
        overlay = json.load(f)
    for player in scoreboard.get("players", []):
        row = player.get("row") or player.get("row_number")
        overlay_row = next((o for o in overlay if o.get("row") == row), None)
        if overlay_row:
            player["level"] = overlay_row.get("level")
            player["gold"] = overlay_row.get("gold")
            player["health"] = overlay_row.get("health")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(scoreboard, f, indent=2, ensure_ascii=False)
    print(f"Merged scoreboard written to {OUTPUT_PATH}")

if __name__ == "__main__":
    merge_scoreboard_and_overlay() 