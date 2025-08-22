"""
Go Stealth AI Launcher - Compact Progress Display
"""
import os
import sys
import time
import subprocess
import threading
import requests
from packaging import version

def setup_console():
    """Setup small, custom console window"""
    if sys.platform == "win32":
        import ctypes
        
        # Get console window handle
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        
        hWnd = kernel32.GetConsoleWindow()
        if hWnd:
            # Set console size (small)
            os.system('mode con: cols=50 lines=15')
            
            # Set console title
            kernel32.SetConsoleTitleW("GoStealthAI Launcher")
            
            # Set console color (dark blue background, bright white text)
            os.system('color 1F')
            
            # Center the console window
            user32.SetWindowPos(hWnd, 0, 500, 300, 400, 300, 0x0040)

def show_compact_progress(message, progress=0):
    """Show compact progress bar"""
    bar_length = 30
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"  {bar} {progress}%", end='\r')
    if progress >= 100:
        print(f"  {bar} ✓ {message}")

def launch_main():
    """Launch with compact display"""
    try:
        # Setup console
        setup_console()
        
        # Clear and show header
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("╔══════════════════════════════════════════════╗")
        print("║         GOSTEALTHAI LAUNCHER v1.0.1         ║")
        print("║            Gemini 2.5 Pro (65535)            ║")
        print("╚══════════════════════════════════════════════╝")
        print()
        
        # Progress sequence
        steps = [
            ("Loading core modules", 20),
            ("Initializing Gemini 2.5 Pro", 40),
            ("Setting up capture system", 60),
            ("Loading user interface", 80),
            ("Starting application", 100)
        ]
        
        for message, progress in steps:
            show_compact_progress(message, progress)
            time.sleep(0.3)
        
        print()
        print("─" * 48)
        print("  ✅ Ready! Launching application...")
        print("─" * 48)
        
        # Import and run main app
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from main_simple import main
        
        # Start main app in new thread
        app_thread = threading.Thread(target=main, daemon=False)
        app_thread.start()
        
        # Quick countdown
        for i in range(2, 0, -1):
            print(f"  Closing in {i}...", end='\r')
            time.sleep(1)
        
        # Hide console
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.WinDLL('kernel32')
            user32 = ctypes.WinDLL('user32')
            hWnd = kernel32.GetConsoleWindow()
            if hWnd:
                user32.ShowWindow(hWnd, 0)
        
        # Wait for app
        app_thread.join()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    launch_main()