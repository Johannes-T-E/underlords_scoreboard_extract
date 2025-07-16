import os
from PIL import Image
import cv2
import numpy as np

# Coordinates from analyze_overlay.py
player_level_x_start = 0
player_level_x_end = 25
player_level_y_start = 34
player_level_y_end = 56

player_gold_x_start = 40
player_gold_x_end = 70
player_gold_y_start = 34
player_gold_y_end = 56

player_health_x_start = 150
player_health_x_end = 202
player_health_y_start = 18
player_health_y_end = 48

# Add these from analyze_overlay.py
row_height = 64
num_players = 8

# Overlay offset
overlay_x = 100
overlay_y = 100

def crop_area(img, x_start, x_end, y_start, y_end, row):
    y_offset = overlay_y + row * row_height
    x_offset = overlay_x
    return img.crop((x_offset + x_start, y_offset + y_start, x_offset + x_end, y_offset + y_end))

input_dir = 'assets/templates/screenshots_for_templates'
output_base = 'assets/templates/cropped_ooc'

level_dir = os.path.join(output_base, 'level')
gold_dir = os.path.join(output_base, 'gold')
health_dir = os.path.join(output_base, 'health')

os.makedirs(level_dir, exist_ok=True)
os.makedirs(gold_dir, exist_ok=True)
os.makedirs(health_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if 'OOC' not in filename or not filename.lower().endswith('.png'):
        continue
    img_path = os.path.join(input_dir, filename)
    img = Image.open(img_path)

    for row in range(num_players):
        # Crop level
        level_crop = crop_area(img, player_level_x_start, player_level_x_end, player_level_y_start, player_level_y_end, row)
        level_np = np.array(level_crop)
        level_gray = cv2.cvtColor(level_np, cv2.COLOR_RGB2GRAY)
        _, level_bin = cv2.threshold(level_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        level_path = os.path.join(level_dir, f'{os.path.splitext(filename)[0]}_row{row}_level.png')
        cv2.imwrite(level_path, level_bin)

        # Crop gold
        gold_crop = crop_area(img, player_gold_x_start, player_gold_x_end, player_gold_y_start, player_gold_y_end, row)
        gold_np = np.array(gold_crop)
        gold_gray = cv2.cvtColor(gold_np, cv2.COLOR_RGB2GRAY)
        _, gold_bin = cv2.threshold(gold_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        gold_path = os.path.join(gold_dir, f'{os.path.splitext(filename)[0]}_row{row}_gold.png')
        cv2.imwrite(gold_path, gold_bin)

        # Crop health
        health_crop = crop_area(img, player_health_x_start, player_health_x_end, player_health_y_start, player_health_y_end, row)
        health_np = np.array(health_crop)
        health_gray = cv2.cvtColor(health_np, cv2.COLOR_RGB2GRAY)
        _, health_bin = cv2.threshold(health_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        health_path = os.path.join(health_dir, f'{os.path.splitext(filename)[0]}_row{row}_health.png')
        cv2.imwrite(health_path, health_bin)

print('Cropping and binarization complete!') 