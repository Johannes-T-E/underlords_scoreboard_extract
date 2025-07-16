import cv2
import os
import json
from datetime import datetime
import re

class PlayerTemplateManager:
    """Manages player name templates for fast recognition."""
    def __init__(self, templates_dir="assets/templates/players", players_db="assets/players_database.json"):
        self.templates_dir = templates_dir
        self.scoreboard_templates_dir = os.path.join(self.templates_dir, "scoreboard")
        self.overlay_templates_dir = os.path.join(self.templates_dir, "overlay")
        os.makedirs(self.scoreboard_templates_dir, exist_ok=True)
        os.makedirs(self.overlay_templates_dir, exist_ok=True)
        self.players_db_path = players_db
        self.players_db = self._load_players_database()
        self.templates_cache = {}
        os.makedirs(templates_dir, exist_ok=True)
        os.makedirs(os.path.dirname(players_db), exist_ok=True)

    def _load_players_database(self):
        if os.path.exists(self.players_db_path):
            try:
                with open(self.players_db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "next_template_id": 1,
            "players": {}
        }

    def _save_players_database(self):
        with open(self.players_db_path, 'w', encoding='utf-8') as f:
            json.dump(self.players_db, f, indent=2, ensure_ascii=False)

    def _convert_to_binary(self, image):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return binary

    def find_player_by_template(self, name_image, threshold=0.99):
        name_image_binary = self._convert_to_binary(name_image)
        best_match = None
        best_confidence = 0.0
        for player_id, player_info in self.players_db["players"].items():
            for key in ["scoreboard_template_path", "overlay_template_path"]:
                template_path = player_info.get(key)
                if not template_path or not os.path.exists(template_path):
                    continue
                template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                if template is None:
                    continue
                template_binary = self._convert_to_binary(template)
                if template_binary.shape != name_image_binary.shape:
                    template_resized = cv2.resize(template_binary, (name_image_binary.shape[1], name_image_binary.shape[0]))
                else:
                    template_resized = template_binary
                result = cv2.matchTemplate(name_image_binary, template_resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                if max_val > best_confidence:
                    best_confidence = max_val
                    best_match = {
                        "player_id": player_id,
                        "player_name": player_info.get("name", f"Player_{player_id}"),
                        "template_path": template_path,
                        "confidence": max_val
                    }
        if best_match and best_confidence >= threshold:
            return best_match
        return None

    def add_new_player(self, player_name_crop, player_name, template_type="scoreboard", player_id=None):
        # If player_id is provided, use it; otherwise, assign a new one
        if player_id is None:
            template_id = self.players_db.get("next_template_id", 1)
            self.players_db["next_template_id"] = template_id + 1
        else:
            template_id = int(player_id)
        if str(template_id) not in self.players_db["players"]:
            self.players_db["players"][str(template_id)] = {}
        # Always update the name label
        self.players_db["players"][str(template_id)]["name"] = player_name
        if template_type == "scoreboard":
            template_dir = self.scoreboard_templates_dir
            template_key = "scoreboard_template_path"
        elif template_type == "overlay":
            template_dir = self.overlay_templates_dir
            template_key = "overlay_template_path"
        else:
            template_dir = self.templates_dir
            template_key = "template_path"
        os.makedirs(template_dir, exist_ok=True)
        template_filename = f"player_{template_id:03d}.png"
        template_path = os.path.join(template_dir, template_filename)
        player_name_crop_binary = self._convert_to_binary(player_name_crop)
        success = cv2.imwrite(template_path, player_name_crop_binary)
        if not success:
            print(f"Warning: Failed to write template image for {player_name} to {template_path}")
        else:
            print(f"Template image written: {template_path}")
        self.players_db["players"][str(template_id)][template_key] = template_path
        self.players_db["players"][str(template_id)]["template_id"] = template_id
        self._save_players_database()
        return template_id

    def get_all_players(self):
        return [(info.get("name", f"Player_{player_id}"), int(player_id)) for player_id, info in self.players_db["players"].items()] 