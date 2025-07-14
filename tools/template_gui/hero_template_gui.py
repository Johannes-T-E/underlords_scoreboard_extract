import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import os
from pathlib import Path
from PIL import Image, ImageTk

# Add test modules and components
#import sys
#sys.path.append('.')
from test_hero_slots import calculate_hero_slots, get_fixed_row_boundaries
from column_detection import find_column_headers_complete
from create_custom_templates import process_slot_for_template, extract_templates_from_screenshot, check_template_coverage

class TemplateCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Underlords Template Creator")
        self.root.geometry("1400x900")
        
        # Data
        self.screenshot_path = None
        self.screenshot_image = None
        self.display_image = None
        self.hero_mappings = {}
        self.crew_slots = []
        self.bench_slots = []
        self.row_starts = []
        self.selected_slot = None
        
        # Load hero names from icon folder
        self.hero_names = self.load_hero_names()
        
        self.setup_ui()
        
    def load_hero_names(self):
        """Load hero names from the icon folder, excluding those with existing templates."""
        hero_icons_dir = Path('assets/icons/hero_icons_scaled_56x56')
        all_heroes = []
        
        if hero_icons_dir.exists():
            for icon_path in hero_icons_dir.glob('*.png'):
                hero_name = icon_path.stem.replace('npc_dota_hero_', '').replace('_png', '')
                all_heroes.append(hero_name)
        
        # Get heroes that already have templates in custom_templates\masks
        existing_templates = set()
        custom_templates_dir = Path('custom_templates/masks')
        if custom_templates_dir.exists():
            for template_path in custom_templates_dir.glob('*.png'):
                hero_name = template_path.stem.replace('_mask', '')
                existing_templates.add(hero_name)
        
        # Return only heroes without templates
        available_heroes = [hero for hero in all_heroes if hero not in existing_templates]
        return sorted(available_heroes)
    
    def refresh_hero_list(self):
        """Refresh the hero dropdown list, excluding newly created templates."""
        self.hero_names = self.load_hero_names()
        self.hero_combo['values'] = self.hero_names
        
        # Clear current selection if the hero now has a template
        current_hero = self.hero_var.get()
        if current_hero and current_hero not in self.hero_names:
            self.hero_var.set("")
    
    def setup_ui(self):
        """Setup the GUI layout."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls
        left_panel = ttk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Right panel - Image display
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.setup_left_panel(left_panel)
        self.setup_right_panel(right_panel)
    
    def setup_left_panel(self, panel):
        """Setup the left control panel."""
        # Title
        title_label = ttk.Label(panel, text="Template Creator", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Screenshot section
        screenshot_frame = ttk.LabelFrame(panel, text="Screenshot", padding=10)
        screenshot_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.load_button = ttk.Button(screenshot_frame, text="Load Screenshot", 
                                     command=self.load_screenshot)
        self.load_button.pack(fill=tk.X)
        
        self.screenshot_label = ttk.Label(screenshot_frame, text="No screenshot loaded", 
                                         foreground="gray")
        self.screenshot_label.pack(pady=(5, 0))
        
        # Hero selection section
        hero_frame = ttk.LabelFrame(panel, text="Hero Selection", padding=10)
        hero_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(hero_frame, text="Selected Slot:").pack(anchor=tk.W)
        self.slot_label = ttk.Label(hero_frame, text="None", foreground="blue", 
                                   font=("Arial", 10, "bold"))
        self.slot_label.pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(hero_frame, text="Hero:").pack(anchor=tk.W)
        self.hero_var = tk.StringVar()
        self.hero_combo = ttk.Combobox(hero_frame, textvariable=self.hero_var, 
                                      values=self.hero_names, state="readonly", 
                                      font=("Arial", 12))
        self.hero_combo.pack(fill=tk.X, pady=(0, 10))
        
        self.assign_button = ttk.Button(hero_frame, text="Assign Hero to Slot", 
                                       command=self.assign_hero, state="disabled")
        self.assign_button.pack(fill=tk.X)
        
        # Current mappings section
        mappings_frame = ttk.LabelFrame(panel, text="Current Mappings", padding=10)
        mappings_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrollable text widget for mappings
        mappings_scroll_frame = ttk.Frame(mappings_frame)
        mappings_scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        self.mappings_text = tk.Text(mappings_scroll_frame, height=8, width=30, 
                                    font=("Consolas", 9))
        mappings_scrollbar = ttk.Scrollbar(mappings_scroll_frame, orient=tk.VERTICAL, 
                                          command=self.mappings_text.yview)
        self.mappings_text.configure(yscrollcommand=mappings_scrollbar.set)
        
        self.mappings_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mappings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Clear button
        self.clear_button = ttk.Button(mappings_frame, text="Clear All Mappings", 
                                      command=self.clear_mappings)
        self.clear_button.pack(fill=tk.X, pady=(10, 0))
        
        # Actions section
        actions_frame = ttk.LabelFrame(panel, text="Actions", padding=10)
        actions_frame.pack(fill=tk.X)
        
        self.extract_button = ttk.Button(actions_frame, text="Extract Templates", 
                                        command=self.extract_templates, state="disabled")
        self.extract_button.pack(fill=tk.X, pady=(0, 5))
        
        self.coverage_button = ttk.Button(actions_frame, text="Check Coverage", 
                                         command=self.check_coverage)
        self.coverage_button.pack(fill=tk.X)
    
    def setup_right_panel(self, panel):
        """Setup the right image display panel."""
        # Image canvas with scrollbars
        canvas_frame = ttk.Frame(panel)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="lightgray")
        
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind canvas click
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        
        # Instructions
        instructions_frame = ttk.Frame(panel)
        instructions_frame.pack(fill=tk.X, pady=(10, 0))
        
        instructions = """Instructions:
1. Load a screenshot using "Load Screenshot"
2. Click on any hero slot in the image
3. Select the hero name from the dropdown
4. Click "Assign Hero to Slot"
5. Repeat for all visible heroes
6. Click "Extract Templates" to save"""
        
        ttk.Label(instructions_frame, text=instructions, justify=tk.LEFT, 
                 foreground="darkblue").pack(anchor=tk.W)
    
    def load_screenshot(self):
        """Load a screenshot file."""
        file_path = filedialog.askopenfilename(
            title="Select Screenshot",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff"),
                ("PNG files", "*.png"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            # Load image with OpenCV
            self.screenshot_image = cv2.imread(file_path)
            if self.screenshot_image is None:
                raise ValueError("Failed to load image")
            
            self.screenshot_path = file_path
            
            # Process screenshot to find slots
            self.process_screenshot()
            
            # Display image
            self.display_screenshot()
            
            # Update UI
            filename = os.path.basename(file_path)
            self.screenshot_label.config(text=f"Loaded: {filename}", foreground="green")
            self.extract_button.config(state="normal")
            
            # Refresh hero list in case templates were created outside the GUI
            self.refresh_hero_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load screenshot:\n{str(e)}")
    
    def process_screenshot(self):
        """Process screenshot to find hero slots."""
        try:
            # Get column headers and calculate slots
            headers, _ = find_column_headers_complete(self.screenshot_image)
            if not headers:
                raise ValueError("No column headers found")
            
            # Get column positions
            crew_start_x = headers.get('CREW', [None])[0] if 'CREW' in headers else None
            crew_end_x = headers.get('UNDERLORD', [None])[0] if 'UNDERLORD' in headers else None
            bench_start_x = headers.get('BENCH', [None])[0] if 'BENCH' in headers else None
            
            if not crew_start_x or not crew_end_x:
                raise ValueError("Required columns not found")
            
            # Calculate slots
            self.crew_slots = calculate_hero_slots(crew_start_x, crew_end_x)
            self.bench_slots = calculate_hero_slots(bench_start_x, self.screenshot_image.shape[1], max_slots=8) if bench_start_x else []
            
            # Get row boundaries  
            self.row_starts = get_fixed_row_boundaries()
            
            print(f"Found {len(self.crew_slots)} crew slots, {len(self.bench_slots)} bench slots")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process screenshot:\n{str(e)}")
            raise
    
    def display_screenshot(self):
        """Display screenshot with slot overlays."""
        if self.screenshot_image is None:
            return
        
        # Create display image with slot overlays
        display_img = self.screenshot_image.copy()
        
        # Draw slot rectangles
        for row_idx in range(min(len(self.row_starts) - 1, 8)):
            row_start = self.row_starts[row_idx]
            
            # Draw CREW slots
            for slot_idx, (slot_start, slot_end, slot_center) in enumerate(self.crew_slots):
                slot_top = row_start + 5
                slot_bottom = slot_top + 56
                
                slot_id = f"row{row_idx+1}crew{slot_idx}"
                
                # Determine color and thickness based on state
                if slot_id == self.selected_slot:
                    color = (0, 0, 255)  # Red for selected
                    thickness = 4
                elif slot_id in self.hero_mappings:
                    color = (0, 255, 0)  # Green for mapped
                    thickness = 2
                else:
                    color = (255, 255, 0)  # Yellow for unmapped
                    thickness = 1
                
                cv2.rectangle(display_img, (slot_start, slot_top), (slot_end, slot_bottom), color, thickness)
                
                # Add slot label
                label = f"R{row_idx+1}C{slot_idx}"
                cv2.putText(display_img, label, (slot_start + 2, slot_top + 12), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
                
                # Add special highlight for selected slot
                if slot_id == self.selected_slot:
                    # Draw inner highlight
                    cv2.rectangle(display_img, (slot_start + 2, slot_top + 2), 
                                (slot_end - 2, slot_bottom - 2), (0, 0, 255), 2)
                    # Add "SELECTED" text
                    cv2.putText(display_img, "SELECTED", (slot_start + 2, slot_bottom - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            
            # Draw BENCH slots
            for slot_idx, (slot_start, slot_end, slot_center) in enumerate(self.bench_slots):
                slot_top = row_start + 5
                slot_bottom = slot_top + 56
                
                slot_id = f"row{row_idx+1}bench{slot_idx}"
                
                # Determine color and thickness based on state
                if slot_id == self.selected_slot:
                    color = (0, 0, 255)  # Red for selected
                    thickness = 4
                elif slot_id in self.hero_mappings:
                    color = (0, 255, 0)  # Green for mapped
                    thickness = 2
                else:
                    color = (255, 0, 255)  # Magenta for unmapped
                    thickness = 1
                
                cv2.rectangle(display_img, (slot_start, slot_top), (slot_end, slot_bottom), color, thickness)
                
                # Add slot label
                label = f"R{row_idx+1}B{slot_idx}"
                cv2.putText(display_img, label, (slot_start + 2, slot_top + 12), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
                
                # Add special highlight for selected slot
                if slot_id == self.selected_slot:
                    # Draw inner highlight
                    cv2.rectangle(display_img, (slot_start + 2, slot_top + 2), 
                                (slot_end - 2, slot_bottom - 2), (0, 0, 255), 2)
                    # Add "SELECTED" text
                    cv2.putText(display_img, "SELECTED", (slot_start + 2, slot_bottom - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # Convert to PIL and display
        display_img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(display_img_rgb)
        
        # Scale down if too large
        max_display_width = 1000
        if pil_img.width > max_display_width:
            scale_factor = max_display_width / pil_img.width
            new_width = int(pil_img.width * scale_factor)
            new_height = int(pil_img.height * scale_factor)
            pil_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        self.display_image = ImageTk.PhotoImage(pil_img)
        
        # Update canvas
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.display_image)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_canvas_click(self, event):
        """Handle canvas click to select slot."""
        if self.screenshot_image is None:
            return
        
        # Get click coordinates (account for canvas scrolling)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Scale coordinates back to original image size if display was scaled
        if self.display_image:
            display_width = self.display_image.width()
            original_width = self.screenshot_image.shape[1]
            if display_width != original_width:
                scale_factor = original_width / display_width
                canvas_x = int(canvas_x * scale_factor)
                canvas_y = int(canvas_y * scale_factor)
        
        # Find which slot was clicked
        clicked_slot = self.find_slot_at_position(canvas_x, canvas_y)
        
        if clicked_slot:
            self.selected_slot = clicked_slot
            self.slot_label.config(text=clicked_slot)
            self.assign_button.config(state="normal")
            
            # If this slot already has a hero assigned, show it
            if clicked_slot in self.hero_mappings:
                current_hero = self.hero_mappings[clicked_slot]
                self.hero_var.set(current_hero)
            
            # Update display to show selection highlight
            self.display_screenshot()
        else:
            self.selected_slot = None
            self.slot_label.config(text="None")
            self.assign_button.config(state="disabled")
            
            # Update display to clear selection highlight
            self.display_screenshot()
    
    def find_slot_at_position(self, x, y):
        """Find which slot contains the given coordinates."""
        for row_idx in range(min(len(self.row_starts) - 1, 8)):
            row_start = self.row_starts[row_idx]
            slot_top = row_start + 5
            slot_bottom = slot_top + 56
            
            if not (slot_top <= y <= slot_bottom):
                continue
            
            # Check CREW slots
            for slot_idx, (slot_start, slot_end, slot_center) in enumerate(self.crew_slots):
                if slot_start <= x <= slot_end:
                    return f"row{row_idx+1}crew{slot_idx}"
            
            # Check BENCH slots
            for slot_idx, (slot_start, slot_end, slot_center) in enumerate(self.bench_slots):
                if slot_start <= x <= slot_end:
                    return f"row{row_idx+1}bench{slot_idx}"
        
        return None
    
    def assign_hero(self):
        """Assign selected hero to selected slot."""
        if not self.selected_slot or not self.hero_var.get():
            messagebox.showwarning("Warning", "Please select both a slot and a hero.")
            return
        
        hero_name = self.hero_var.get()
        slot_id = self.selected_slot
        
        # Check if hero is already assigned to another slot
        existing_slot = None
        for existing_slot_id, existing_hero in self.hero_mappings.items():
            if existing_hero == hero_name and existing_slot_id != slot_id:
                existing_slot = existing_slot_id
                break
        
        if existing_slot:
            result = messagebox.askyesno("Duplicate Hero", 
                                       f"{hero_name} is already assigned to {existing_slot}.\n"
                                       f"Move it to {slot_id}?")
            if result:
                del self.hero_mappings[existing_slot]
            else:
                return
        
        # Assign hero
        self.hero_mappings[slot_id] = hero_name
        
        # Update display
        self.update_mappings_display()
        self.display_screenshot()  # Refresh to show updated slot colors
        
        # Clear selection
        self.selected_slot = None
        self.slot_label.config(text="None")
        self.hero_var.set("")
        self.assign_button.config(state="disabled")
        
        # Update display to clear selection highlight
        self.display_screenshot()
    
    def update_mappings_display(self):
        """Update the mappings text display."""
        self.mappings_text.delete(1.0, tk.END)
        
        if not self.hero_mappings:
            self.mappings_text.insert(tk.END, "No mappings yet...")
            return
        
        # Sort by slot for better readability
        sorted_mappings = sorted(self.hero_mappings.items())
        
        for slot_id, hero_name in sorted_mappings:
            self.mappings_text.insert(tk.END, f"{slot_id}: {hero_name}\n")
        
        self.mappings_text.insert(tk.END, f"\nTotal: {len(self.hero_mappings)} heroes")
    
    def clear_mappings(self):
        """Clear all current mappings."""
        if self.hero_mappings:
            result = messagebox.askyesno("Clear Mappings", 
                                       f"Clear all {len(self.hero_mappings)} mappings?")
            if result:
                self.hero_mappings.clear()
                self.selected_slot = None
                self.slot_label.config(text="None")
                self.hero_var.set("")
                self.assign_button.config(state="disabled")
                self.update_mappings_display()
                self.display_screenshot()
    
    def extract_templates(self):
        """Extract templates using current mappings."""
        if not self.hero_mappings:
            messagebox.showwarning("Warning", "No hero mappings defined.")
            return
        
        if not self.screenshot_path:
            messagebox.showerror("Error", "No screenshot loaded.")
            return
        
        try:
            # Run extraction
            success = extract_templates_from_screenshot(
                self.screenshot_path, 
                self.hero_mappings, 
                output_dir="custom_templates"
            )
            
            if success:
                messagebox.showinfo("Success", 
                                  f"Successfully extracted {len(self.hero_mappings)} templates!\n\n"
                                  f"Saved to: custom_templates/\n"
                                  f"Check the coverage report for progress.")
                
                # Refresh hero list to exclude newly created templates
                self.refresh_hero_list()
                
                # Auto-show coverage
                self.check_coverage()
            else:
                messagebox.showerror("Error", "Template extraction failed.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Extraction failed:\n{str(e)}")
    
    def check_coverage(self):
        """Check and display template coverage."""
        try:
            existing_templates, missing_heroes = check_template_coverage("custom_templates")
            
            total_heroes = len(existing_templates) + len(missing_heroes)
            coverage_pct = len(existing_templates) / total_heroes * 100 if total_heroes > 0 else 0
            
            message = f"TEMPLATE COVERAGE REPORT\n\n"
            message += f"Total heroes: {total_heroes}\n"
            message += f"Templates created: {len(existing_templates)}\n"
            message += f"Still missing: {len(missing_heroes)}\n"
            message += f"Coverage: {coverage_pct:.1f}%\n\n"
            
            if missing_heroes:
                message += f"Missing heroes ({len(missing_heroes)}):\n"
                # Show first 20 missing heroes
                missing_to_show = missing_heroes[:20]
                for i, hero in enumerate(missing_to_show):
                    if i % 4 == 0:
                        message += "\n"
                    message += f"{hero:<15}"
                
                if len(missing_heroes) > 20:
                    message += f"\n... and {len(missing_heroes) - 20} more"
            
            messagebox.showinfo("Template Coverage", message)
            
        except Exception as e:
            messagebox.showerror("Error", f"Coverage check failed:\n{str(e)}")

def main():
    """Main function to run the GUI."""
    root = tk.Tk()
    app = TemplateCreatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 