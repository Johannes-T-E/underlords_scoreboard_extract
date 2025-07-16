import pyautogui
import pygetwindow as gw
import keyboard
import time
import os
from datetime import datetime
from PIL import Image
import threading
import mss
import win32gui
import win32con
import win32ui

class UnderlordScreenshotTool:
    def __init__(self, output_dir="screenshots"):
        self.output_dir = output_dir
        self.window = None
        self.running = False
        self.screenshot_count = 0
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Disable pyautogui fail-safe (prevents mouse from going to corner)
        pyautogui.FAILSAFE = False
        
    def find_underlords_window(self):
        """Find the Dota Underlords window."""
        try:
            # Try different possible window titles
            possible_titles = [
                "Dota Underlords",
                "Dota Underlords - Steam",
                "Dota Underlords - Valve",
                "Underlords"
            ]
            
            for title in possible_titles:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    self.window = windows[0]
                    #print(f"Found Underlords window: '{self.window.title}'")
                    #print(f"Window position: {self.window.left}, {self.window.top}")
                    #print(f"Window size: {self.window.width} x {self.window.height}")
                    return True
            
            # If exact match fails, try partial match
            all_windows = gw.getAllWindows()
            for window in all_windows:
                if "underlords" in window.title.lower() or "dota" in window.title.lower():
                    self.window = window
                    #print(f"Found possible Underlords window: '{self.window.title}'")
                    #print(f"Window position: {self.window.left}, {self.window.top}")
                    #print(f"Window size: {self.window.width} x {self.window.height}")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error finding window: {e}")
            return False
    
    def get_hwnd(self):
        """Get the window handle (HWND) for the Underlords window."""
        if self.window:
            return self.window._hWnd
        return None

    def capture_window_gdi(self, hwnd, y_start=37, y_end=770):
        """Capture the window content using GDI BitBlt, crop to scoreboard area."""
        # Get window client area size
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        width = right - left
        height = bottom - top

        # Get window device context
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        # Create a bitmap object
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)

        # BitBlt (copy window content to bitmap)
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

        # Convert to PIL Image
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)

        # Crop to scoreboard area
        img = img.crop((0, y_start, width, y_end))

        # Remove 2px left border
        img = img.crop((2, 0, img.width, img.height))

        # Cleanup
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        return img

    def take_scoreboard_screenshot(self, save_to_disk=False):
        """Take a screenshot of only the scoreboard area (y=0 to y=733 in window content) using GDI BitBlt. Returns PIL image."""
        hwnd = self.get_hwnd()
        if not hwnd:
            print("No Underlords window found!")
            return None
        try:
            img = self.capture_window_gdi(hwnd, y_start=37, y_end=770)
            if save_to_disk:
                filename = "SS_Latest.png"
                filepath = os.path.join(self.output_dir, filename)
                img.save(filepath)
            self.screenshot_count += 1
            return img  # Return the PIL image
        except Exception as e:
            print(f"Error taking screenshot: {e}")
            return None
    
    def refresh_window_info(self):
        """Refresh window information in case it moved or resized."""
        if self.window:
            try:
                # Update window info
                self.window = gw.getWindowsWithTitle(self.window.title)[0]
                return True
            except:
                print("Window may have been closed. Searching for new window...")
                return self.find_underlords_window()
        return False
    
    def start_monitoring(self):
        """Start monitoring for key presses."""
        self.running = True
        
        print("=== Dota Underlords Screenshot Tool ===")
        print("Instructions:")
        print("- Press 'P' to take a screenshot of the scoreboard area (y=0 to y=733)")
        print("- Press 'R' to refresh window information")
        print("- Press 'Q' to quit")
        print("- Press 'H' to show this help")
        print()
        
        if not self.find_underlords_window():
            print("ERROR: Could not find Dota Underlords window!")
            print("Make sure Dota Underlords is running and visible.")
            return
        
        print("Monitoring for key presses... (Press 'Q' to quit)")
        
        while self.running:
            try:
                if keyboard.is_pressed('p'):
                    self.refresh_window_info()
                    self.take_scoreboard_screenshot()
                    time.sleep(0.5)  # Prevent multiple screenshots from one press
                    
                elif keyboard.is_pressed('r'):
                    print("Refreshing window information...")
                    self.refresh_window_info()
                    time.sleep(0.5)
                    
                elif keyboard.is_pressed('q'):
                    print("Quitting...")
                    self.running = False
                    break
                    
                elif keyboard.is_pressed('h'):
                    print("\nHelp:")
                    print("P = Take scoreboard screenshot (y=0 to y=733)")
                    print("R = Refresh window info")
                    print("Q = Quit")
                    print("H = Show help")
                    print()
                    time.sleep(0.5)
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            except KeyboardInterrupt:
                print("\nExiting...")
                self.running = False
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(1)
    
    def take_single_screenshot(self, save_to_disk=False):
        """Take a single screenshot and return the PIL image (in memory). Only search for window if lost."""
        if self.window is None or not self.refresh_window_info():
            if not self.find_underlords_window():
                return None
        return self.take_scoreboard_screenshot(save_to_disk=save_to_disk)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Screenshot tool for Dota Underlords")
    parser.add_argument('--output', '-o', default='screenshots', 
                       help='Output directory for screenshots (default: screenshots)')
    parser.add_argument('--single', '-s', action='store_true',
                       help='Take a single screenshot and exit')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Test window detection only')
    
    args = parser.parse_args()
    
    tool = UnderlordScreenshotTool(output_dir=args.output)
    
    if args.test:
        print("Testing window detection...")
        if tool.find_underlords_window():
            print("✓ Window found successfully!")
        else:
            print("✗ Window not found!")
        return
    
    if args.single:
        print("Taking single screenshot...")
        if tool.take_single_screenshot():
            print("✓ Screenshot taken successfully!")
        else:
            print("✗ Failed to take screenshot!")
        return
    
    # Default: start monitoring mode
    try:
        tool.start_monitoring()
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main() 