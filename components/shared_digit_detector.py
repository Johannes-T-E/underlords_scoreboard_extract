import cv2
import numpy as np
import os
import glob
import re

class SharedDigitDetector:
    """Shared digit detector that uses template matching for all extraction types."""
    
    def __init__(self, templates_dir="assets/templates/digits"):
        self.templates_dir = templates_dir
        self._templates_cache = {}
        self._load_all_templates()
    
    def _load_all_templates(self):
        """Load all digit templates and cache them."""
        # Template patterns for different extraction types
        template_patterns = {
            'health': r'health_digit_(\d)\.png',
            'record': r'record_digit_(\d)\.png',
            'networth': r'NetWorth_digit_(\d)\.png',
            'player': r'(\d)\.png',  # Generic digit templates
            'record_separator': r'record_digit_separator\.png'
        }
        
        # Initialize cache structure
        self._templates_cache = {
            'health': {},
            'record': {},
            'networth': {},
            'player': {},
            'record_separator': None
        }
        
        # Load all template files
        template_files = glob.glob(os.path.join(self.templates_dir, "*.png"))
        
        for template_file in template_files:
            filename = os.path.basename(template_file)
            
            # Check each pattern
            for template_type, pattern in template_patterns.items():
                match = re.match(pattern, filename)
                if match:
                    if template_type == 'record_separator':
                        # Special case for separator
                        template = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
                        if template is not None:
                            self._templates_cache['record_separator'] = self._convert_to_binary(template)
                    else:
                        # Regular digit templates
                        digit_value = int(match.group(1))
                        template = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
                        if template is not None:
                            self._templates_cache[template_type][digit_value] = self._convert_to_binary(template)
                    break
    
    def _convert_to_binary(self, image):
        """Convert image to binary for consistent template matching."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return binary
    
    def get_digit_templates(self, template_type):
        """Get digit templates for a specific extraction type."""
        return self._templates_cache.get(template_type, {})
    
    def get_separator_template(self):
        """Get the record separator template."""
        return self._templates_cache.get('record_separator')
    
    def find_all_digit_matches(self, region, template_type, confidence_threshold=0.97):
        """Find all digit matches in a region using template matching (no sliding)."""
        if region.size == 0:
            return []
        
        # Get templates for this extraction type
        templates = self.get_digit_templates(template_type)
        if not templates:
            return []
        
        region_binary = self._convert_to_binary(region)
        all_matches = []
        
        # For each digit template, find all matches above threshold
        for digit_value, template in templates.items():
            # Perform template matching on entire region
            result = cv2.matchTemplate(region_binary, template, cv2.TM_CCOEFF_NORMED)
            
            # Find all locations where matching is above threshold
            locations = np.where(result >= confidence_threshold)
            
            # Convert to list of matches
            for y, x in zip(locations[0], locations[1]):
                confidence = result[y, x]
                template_height, template_width = template.shape
                
                all_matches.append({
                    'digit': digit_value,
                    'x_position': x,
                    'y_position': y,
                    'confidence': confidence,
                    'width': template_width,
                    'height': template_height
                })
        
        # Remove overlapping matches (non-maximum suppression)
        filtered_matches = self._remove_overlapping_matches(all_matches)
        
        # Sort by x-position (left to right)
        filtered_matches.sort(key=lambda x: x['x_position'])
        
        return filtered_matches
    
    def _remove_overlapping_matches(self, matches):
        """Remove overlapping matches, keeping the one with highest confidence."""
        if not matches:
            return []
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        filtered = []
        for match in matches:
            # Check if this match overlaps with any already selected match
            overlaps = False
            for selected in filtered:
                if self._matches_overlap(match, selected):
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(match)
        
        return filtered
    
    def _matches_overlap(self, match1, match2):
        """Check if two matches overlap significantly."""
        # Calculate overlap in x-direction
        x1_start, x1_end = match1['x_position'], match1['x_position'] + match1['width']
        x2_start, x2_end = match2['x_position'], match2['x_position'] + match2['width']
        
        # Calculate overlap
        overlap_start = max(x1_start, x2_start)
        overlap_end = min(x1_end, x2_end)
        overlap_width = max(0, overlap_end - overlap_start)
        
        # Consider overlapping if more than 50% of smaller width overlaps
        min_width = min(match1['width'], match2['width'])
        overlap_ratio = overlap_width / min_width
        
        return overlap_ratio > 0.5
    
    def find_digits_by_sliding(self, number_region, template_type, confidence_threshold=0.95):
        """Find all digits in a region using optimized template matching (replaces sliding window)."""
        return self.find_all_digit_matches(number_region, template_type, confidence_threshold)
    
    def find_digits_and_separator_by_sliding(self, record_region, confidence_threshold=0.95):
        """Find all digits and separator in a record region using optimized template matching."""
        if record_region.size == 0:
            return []
        
        # Get digit matches
        digit_matches = self.find_all_digit_matches(record_region, 'record', confidence_threshold)
        
        # Find separator match
        separator_template = self.get_separator_template()
        if separator_template is None:
            return digit_matches
        
        region_binary = self._convert_to_binary(record_region)
        
        # Find separator
        result = cv2.matchTemplate(region_binary, separator_template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= confidence_threshold)
        
        # Add separator matches
        for y, x in zip(locations[0], locations[1]):
            confidence = result[y, x]
            template_height, template_width = separator_template.shape
            
            digit_matches.append({
                'digit': 'separator',
                'x_position': x,
                'y_position': y,
                'confidence': confidence,
                'width': template_width,
                'height': template_height
            })
        
        # Remove overlapping matches and sort by position
        filtered_matches = self._remove_overlapping_matches(digit_matches)
        filtered_matches.sort(key=lambda x: x['x_position'])
        
        return filtered_matches
    
    def reconstruct_number_from_matches(self, matches):
        """Reconstruct a number from digit matches sorted by position."""
        if not matches:
            return None
        
        # Filter out non-digit matches
        digit_matches = [m for m in matches if isinstance(m['digit'], int)]
        
        if not digit_matches:
            return None
        
        # Sort by x-position (should already be sorted)
        digit_matches.sort(key=lambda x: x['x_position'])
        
        # Reconstruct number
        number_str = ''.join(str(match['digit']) for match in digit_matches)
        
        try:
            number = int(number_str)
            avg_confidence = sum(match['confidence'] for match in digit_matches) / len(digit_matches)
            return {
                'number': number,
                'confidence': avg_confidence,
                'digit_count': len(digit_matches)
            }
        except ValueError:
            return None
    
    def reconstruct_record_from_matches(self, matches):
        """Reconstruct wins-losses from matches that include separator."""
        if not matches:
            return None
        
        # Sort by x-position
        matches.sort(key=lambda x: x['x_position'])
        
        # Find separator position
        separator_index = None
        for i, match in enumerate(matches):
            if match['digit'] == 'separator':
                separator_index = i
                break
        
        if separator_index is None:
            return None
        
        # Split into wins (before separator) and losses (after separator)
        wins_matches = [m for m in matches[:separator_index] if isinstance(m['digit'], int)]
        losses_matches = [m for m in matches[separator_index + 1:] if isinstance(m['digit'], int)]
        
        # Reconstruct wins
        wins = None
        if wins_matches:
            wins_str = ''.join(str(match['digit']) for match in wins_matches)
            try:
                wins = int(wins_str)
            except ValueError:
                wins = None
        
        # Reconstruct losses
        losses = None
        if losses_matches:
            losses_str = ''.join(str(match['digit']) for match in losses_matches)
            try:
                losses = int(losses_str)
            except ValueError:
                losses = None
        
        # Calculate average confidence
        all_digit_matches = wins_matches + losses_matches
        avg_confidence = sum(match['confidence'] for match in all_digit_matches) / len(all_digit_matches) if all_digit_matches else 0.0
        
        return {
            'wins': wins,
            'losses': losses,
            'confidence': avg_confidence,
            'total_matches': len(matches)
        }

# Global instance for backward compatibility
shared_detector = SharedDigitDetector() 