"""
Advanced Screen Capture System with Multiple Methods - FIXED
Includes screenshot saving toggle feature
"""
import os
import sys
import time
import numpy as np
from PIL import Image
import win32gui
import win32ui
import win32con
import win32api
import win32clipboard
import mss
import mss.windows
import ctypes
from ctypes import wintypes
import pyautogui
from datetime import datetime
import psutil
import pythoncom
import comtypes
import comtypes.client
from comtypes import CLSCTX_ALL
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Define CAPTUREBLT if not available
if not hasattr(win32con, 'CAPTUREBLT'):
    CAPTUREBLT = 0x40000000
else:
    CAPTUREBLT = win32con.CAPTUREBLT


class AdvancedCapture:
    def __init__(self):
        """Initialize the advanced capture system"""
        print("Initializing Advanced Capture System...")
        
        # Screenshot saving settings (disabled by default)
        self.debug_screenshots = False
        self.screenshot_dir = None
        
        # Initialize MSS properly
        try:
            self.mss_instance = mss.mss()
        except Exception as e:
            print(f"[WARNING] MSS initialization failed: {e}")
            self.mss_instance = None
        
        # Performance settings
        self.last_capture_time = 0
        self.min_capture_interval = 0.1
        
        # Initialize cache
        self.method_cache = {}
        
        # Windows API setup
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # Set DPI awareness
        try:
            self.user32.SetProcessDPIAware()
        except:
            pass
    
    def enable_screenshots(self, enabled=True):
        """Enable/disable screenshot saving"""
        self.debug_screenshots = enabled
        if enabled:
            # Create screenshots directory
            self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
            if not os.path.exists(self.screenshot_dir):
                os.makedirs(self.screenshot_dir)
                print(f"[DEBUG] Created screenshots folder: {self.screenshot_dir}")
        else:
            self.screenshot_dir = None
            print("[DEBUG] Screenshot saving disabled")
    
    def save_debug_screenshot(self, image, method_name):
        """Save screenshot only if enabled"""
        if not self.debug_screenshots or not self.screenshot_dir:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"capture_{timestamp}_{method_name}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            image.save(filepath)
            print(f"[DEBUG] Screenshot saved: {filename}")
        except Exception as e:
            print(f"[ERROR] Could not save screenshot: {e}")
    
    def capture_bitblt_enhanced(self):
        """Enhanced BitBlt capture with better compatibility - FIXED"""
        try:
            print("Trying enhanced BitBlt...")
            
            # Get desktop window
            desktop = win32gui.GetDesktopWindow()
            
            # Get window DC
            hwndDC = win32gui.GetWindowDC(desktop)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Get dimensions
            left, top, right, bot = win32gui.GetWindowRect(desktop)
            width = right - left
            height = bot - top
            
            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # Use SRCCOPY with CAPTUREBLT for layered windows
            # Using the defined CAPTUREBLT constant
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, 
                                 (left, top), win32con.SRCCOPY | CAPTUREBLT)
            
            if result:
                # Convert to PIL Image
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )
                
                # Clean up
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(desktop, hwndDC)
                
                print("[OK] Enhanced BitBlt successful")
                self.save_debug_screenshot(img, "BitBlt")
                return img
            
        except Exception as e:
            print(f"[ERROR] Enhanced BitBlt failed: {e}")
            return None
    
    def capture_mss(self):
        """Capture using MSS (Python Screenshot) - FIXED"""
        try:
            print("Trying MSS capture...")
            
            # Re-initialize MSS if needed
            if self.mss_instance is None:
                try:
                    self.mss_instance = mss.mss()
                except:
                    print("[ERROR] Cannot initialize MSS")
                    return None
            
            # Use with statement for proper context management
            with mss.mss() as sct:
                # Capture primary monitor
                monitor = sct.monitors[1]
                
                # Grab the screen
                sct_img = sct.grab(monitor)
                
                # Convert to PIL Image
                img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
                
                print("[OK] MSS capture successful")
                self.save_debug_screenshot(img, "MSS")
                return img
            
        except Exception as e:
            print(f"[ERROR] MSS capture failed: {e}")
            # Try to clean up MSS instance
            self.mss_instance = None
            return None
    
    def capture_pyautogui(self):
        """Capture using PyAutoGUI - RELIABLE FALLBACK"""
        try:
            print("Trying PyAutoGUI...")
            
            # Take screenshot
            img = pyautogui.screenshot()
            
            print("[OK] PyAutoGUI capture successful")
            self.save_debug_screenshot(img, "PyAutoGUI")
            return img
            
        except Exception as e:
            print(f"[ERROR] PyAutoGUI failed: {e}")
            return None
    
    def capture_simple_bitblt(self):
        """Simple BitBlt without CAPTUREBLT flag"""
        try:
            print("Trying simple BitBlt...")
            
            # Get desktop
            desktop = win32gui.GetDesktopWindow()
            
            # Get dimensions
            left, top, right, bot = win32gui.GetWindowRect(desktop)
            width = right - left
            height = bot - top
            
            # Get DC
            hwndDC = win32gui.GetWindowDC(desktop)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # Simple BitBlt without CAPTUREBLT
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, 
                                 (0, 0), win32con.SRCCOPY)
            
            if result:
                # Convert to PIL
                bmpinfo = saveBitMap.GetInfo()
                bmpstr = saveBitMap.GetBitmapBits(True)
                
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )
                
                # Cleanup
                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(desktop, hwndDC)
                
                print("[OK] Simple BitBlt successful")
                self.save_debug_screenshot(img, "SimpleBitBlt")
                return img
                
        except Exception as e:
            print(f"[ERROR] Simple BitBlt failed: {e}")
            return None
    
    def capture_with_retry(self):
        """Main capture method with multiple fallbacks - REORDERED"""
        methods = [
            ('PyAutoGUI', self.capture_pyautogui),  # Most reliable first
            ('Simple BitBlt', self.capture_simple_bitblt),
            ('Enhanced BitBlt', self.capture_bitblt_enhanced),
            ('MSS', self.capture_mss),
        ]
        
        for method_name, method_func in methods:
            try:
                print(f"Attempting {method_name}...")
                result = method_func()
                if result:
                    print(f"[SUCCESS] Captured using {method_name}")
                    return result
            except Exception as e:
                print(f"[ERROR] {method_name} failed: {e}")
                continue
        
        print("[ERROR] All capture methods failed!")
        return None
    
    def capture_or_extract(self):
        """Main entry point for capture"""
        try:
            # Check for minimum interval between captures
            current_time = time.time()
            if current_time - self.last_capture_time < self.min_capture_interval:
                time.sleep(self.min_capture_interval)
            
            # Try to capture
            screenshot = self.capture_with_retry()
            
            if screenshot:
                self.last_capture_time = time.time()
                return screenshot, 'image'
            else:
                return None, None
                
        except Exception as e:
            print(f"[ERROR] Capture failed: {e}")
            return None, None
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if hasattr(self, 'mss_instance') and self.mss_instance:
                try:
                    self.mss_instance.close()
                except:
                    pass
                self.mss_instance = None
        except:
            pass


# Test function
if __name__ == "__main__":
    capture = AdvancedCapture()
    
    # Enable screenshot saving for testing
    capture.enable_screenshots(True)
    
    result, result_type = capture.capture_or_extract()
    
    if result:
        print(f"Capture successful! Type: {result_type}")
        result.show()
    else:
        print("Capture failed!")
    
    capture.cleanup()