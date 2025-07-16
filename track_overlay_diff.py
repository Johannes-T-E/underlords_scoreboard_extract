import time
import json
import csv
import os
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

OVERLAY_DATA_PATH = 'output/overlay_data.json'
LOG_PATH = 'output/overlay_changes_log.csv'
FIELDS_TO_TRACK = ['row', 'level', 'gold', 'health']

class OverlayDiffHandler(FileSystemEventHandler):
    def __init__(self, overlay_path, log_path):
        self.overlay_path = overlay_path
        self.log_path = log_path
        self.prev_data = None
        # Create log file and write header if it doesn't exist
        if not os.path.exists(log_path):
            with open(log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'row', 'player_name', 'field', 'old_value', 'new_value', 'diff'])

    def on_modified(self, event):
        if os.path.abspath(event.src_path) == os.path.abspath(self.overlay_path):
            try:
                with open(self.overlay_path, 'r', encoding='utf-8') as f:
                    new_data = json.load(f)
            except Exception:
                return  # File may be incomplete, skip this event
            if self.prev_data is None:
                self.prev_data = new_data
                return
            # Compare new_data to prev_data
            for new_row in new_data:
                player_name = new_row.get('player_name')
                if not player_name:
                    continue
                prev_row = next((r for r in self.prev_data if r.get('player_name') == player_name), None)
                if prev_row is None:
                    continue
                row_num = new_row.get('row')
                for field in FIELDS_TO_TRACK:
                    old_val = prev_row.get(field)
                    new_val = new_row.get(field)
                    # Debug output for all fields
                    print(f"DEBUG: {player_name} {field}: {old_val} -> {new_val} (types: {type(old_val)}, {type(new_val)})")
                    if new_val is None or old_val is None:
                        print(f"  SKIPPED: {player_name} {field} - one value is None")
                        continue  # Ignore changes to/from None
                    if new_val != old_val:
                        print(f"CHANGE DETECTED: {player_name} {field}: {old_val} -> {new_val}")
                        # Calculate diff if both values are numbers
                        try:
                            diff = float(new_val) - float(old_val)
                        except (ValueError, TypeError):
                            diff = ''
                        with open(self.log_path, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                datetime.now().isoformat(),
                                row_num,
                                player_name,
                                field,
                                old_val,
                                new_val,
                                diff
                            ])
                    else:
                        print(f"  NO CHANGE: {player_name} {field} - values are the same")
            self.prev_data = new_data

def main():
    event_handler = OverlayDiffHandler(OVERLAY_DATA_PATH, LOG_PATH)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(OVERLAY_DATA_PATH) or '.', recursive=False)
    observer.start()
    print(f"Watching {OVERLAY_DATA_PATH} for changes. Logging diffs to {LOG_PATH}.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main() 