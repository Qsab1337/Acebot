#!/usr/bin/env python3
"""
Go Stealth AI - Complete Version with Ultimate Dynamic Auto-Updater
Version: 1.0.2
Author: GoStealthAI Team
"""
import os
import sys
import time
import threading
import io
import queue
import json
import traceback
from datetime import datetime

# Fix imports for bundled EXE
try:
    from pynput import keyboard, mouse
except ImportError:
    print("[ERROR] pynput not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput"])
    from pynput import keyboard, mouse

# Import other modules with error handling
try:
    from overlay_windows import OverlayWindow
    from advanced_capture import AdvancedCapture
    from simple_ocr import SimpleOCR
    from simple_gemini_provider import SimpleGeminiProvider
    from ultimate_updater import UltimateUpdater  # NEW: Ultimate updater
except ImportError as e:
    print(f"[ERROR] Module import failed: {e}")
    print("[INFO] Make sure all files are in the same directory")
    input("Press Enter to exit...")
    sys.exit(1)

# Version of your app - IMPORTANT: Update this when releasing new versions
APP_VERSION = "1.0.2"
APP_BUILD = "20240115"  # Build date for tracking

def get_resource_path(relative_path):
    """Get path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_data_dir():
    """Get directory for persistent data storage"""
    # Always use user's home directory for data
    home = os.path.expanduser("~")
    data_dir = os.path.join(home, ".GoStealthAI")
    
    # Create directory if it doesn't exist
    try:
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    except Exception as e:
        print(f"[ERROR] Could not create data directory: {e}")
        # Fallback to current directory
        data_dir = os.getcwd()
    
    return data_dir


class APIKeyManager:
    """Secure API key storage manager"""
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.key_file = os.path.join(data_dir, "api_config.json")
        
    def save_key(self, api_key):
        """Save API key securely"""
        try:
            # Simple obfuscation (not encryption, but better than plain text)
            import base64
            encoded = base64.b64encode(api_key.encode()).decode()
            
            data = {
                'key': encoded,
                'saved': datetime.now().isoformat(),
                'version': APP_VERSION
            }
            
            with open(self.key_file, 'w') as f:
                json.dump(data, f)
            
            return True
        except Exception as e:
            print(f"[ERROR] Could not save API key: {e}")
            return False
    
    def load_key(self):
        """Load API key"""
        try:
            if os.path.exists(self.key_file):
                with open(self.key_file, 'r') as f:
                    data = json.load(f)
                
                # Decode the key
                import base64
                encoded = data.get('key', '')
                if encoded:
                    api_key = base64.b64decode(encoded.encode()).decode()
                    if api_key and len(api_key) > 10:
                        return api_key
        except Exception as e:
            print(f"[ERROR] Could not load API key: {e}")
        
        return None


class GoStealthAISimple:
    def __init__(self):
        """Initialize the application with Ultimate Updater"""
        try:
            print("="*50)
            print("Starting Go Stealth AI")
            print(f"Version: {APP_VERSION} (Build {APP_BUILD})")
            print("="*50)
            
            # Initialize Ultimate Updater FIRST
            print("[INFO] Initializing ultimate auto-updater...")
            self.updater = UltimateUpdater(app_instance=self, current_version=APP_VERSION)
            
            # Perform startup update check (non-blocking)
            self.check_for_updates_startup()
            
            # Set up data directory for persistent storage
            self.data_dir = get_data_dir()
            print(f"[INFO] Data directory: {self.data_dir}")
            
            # Initialize API key manager
            self.api_manager = APIKeyManager(self.data_dir)
            
            # Initialize settings file path
            self.settings_file = os.path.join(self.data_dir, "settings.json")
            
            # Initialize components as None first
            self.gemini = None
            self.current_api_key = None
            self.overlay = None
            self.capture = None
            self.ocr = None
            
            # Initialize queue for thread-safe updates
            self.update_queue = queue.Queue()
            
            # Track update state
            self.update_available = False
            self.update_info = {}
            self.auto_update_enabled = True  # Can be toggled in settings
            
            # Load API key
            api_key = self.load_api_key()
            
            # Initialize UI components
            print("[INFO] Initializing UI...")
            self.overlay = OverlayWindow()
            self.overlay.app_reference = self
            
            print("[INFO] Initializing capture system...")
            self.capture = AdvancedCapture()
            
            # Load screenshot setting from saved settings
            self.load_screenshot_setting()
            
            print("[INFO] Initializing OCR...")
            self.ocr = SimpleOCR()
            
            # Initialize Gemini if we have a key
            if api_key:
                self.initialize_gemini(api_key)
                # Update overlay with API status
                self.update_api_status_display()
            else:
                print("[WARNING] No API key found. Set it in settings (Ctrl+Alt+S)")
            
            # Initialize state variables
            self.running = True
            self.is_analyzing = False
            self.screenshot_collection = []
            self.right_click_start = None
            self.right_click_held = False
            
            # Request counter for rate limit awareness
            self.request_count = 0
            self.last_request_reset = time.time()
            
            # Load settings
            self.load_hotkey_settings()
            
            # Setup input listeners
            self.setup_hotkeys()
            self.setup_mouse_listener()
            
            print("\n[OK] All systems ready!")
            self.print_controls()
            
            # Show initial status messages
            self.show_startup_messages()
                
        except Exception as e:
            print(f"[FATAL] Initialization error: {e}")
            traceback.print_exc()
            input("Press Enter to exit...")
            sys.exit(1)

    def check_for_updates_startup(self):
        """Check for updates on startup (non-blocking)"""
        def update_check_thread():
            try:
                # Wait a moment for UI to initialize
                time.sleep(2)
                
                # Check for updates
                success, message = self.updater.check_and_update(auto_apply=False)
                
                if success and "available" in message.lower():
                    # Parse version from message
                    self.update_available = True
                    self.update_info = self.updater.fetch_dynamic_manifest()
                    
                    if self.update_info:
                        version = self.update_info.get('version', 'new')
                        update_type = self.update_info.get('update_requirements', {}).get('update_type', 'hot_reload')
                        
                        # Show notification
                        if update_type == 'hot_reload':
                            # Auto-apply hot-reload updates silently
                            self.safe_update_text(f"🔄 Applying update {version}...")
                            time.sleep(1)
                            success, result_msg = self.updater.check_and_update(auto_apply=True)
                            if success:
                                self.safe_update_text(f"✅ Updated to {version}!")
                            else:
                                self.safe_update_text(f"🎉 Update {version} available!\nPress Ctrl+Alt+U to install")
                        else:
                            # Notify about updates that need restart
                            self.safe_update_text(f"🎉 Update {version} available!\nPress Ctrl+Alt+U to install")
                else:
                    print(f"[UPDATER] {message}")
                    
            except Exception as e:
                print(f"[UPDATER] Startup check error: {e}")
        
        # Start in background
        thread = threading.Thread(target=update_check_thread, daemon=True)
        thread.start()

    def show_startup_messages(self):
        """Show initial status messages"""
        if not self.gemini:
            self.safe_update_text("⚠️ Please set your API key!\nPress Ctrl+Alt+S for settings")
        elif self.update_available:
            version = self.update_info.get('version', 'new')
            self.safe_update_text(f"🎉 Update {version} available!\nPress Ctrl+Alt+U to install")
        else:
            self.safe_update_text(f"GoStealthAI v{APP_VERSION}\nReady to assist!")

    def load_screenshot_setting(self):
        """Load screenshot debug setting"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    if 'save_screenshots' in settings:
                        self.capture.enable_screenshots(settings['save_screenshots'])
                        if settings['save_screenshots']:
                            print("[INFO] Screenshot saving enabled")
        except:
            pass

    def update_api_status_display(self):
        """Update API status in overlay"""
        try:
            if self.overlay and hasattr(self.overlay, 'update_api_status'):
                if self.current_api_key:
                    masked = f"{self.current_api_key[:8]}...{self.current_api_key[-4:]}" if len(self.current_api_key) > 12 else "Set"
                    self.overlay.update_api_status(f"API: {masked}", True)
                else:
                    self.overlay.update_api_status("API: Not Set", False)
        except:
            pass

    def load_api_key(self):
        """Load API key from secure storage"""
        # Try to load from secure storage
        api_key = self.api_manager.load_key()
        
        if api_key:
            print("[OK] API key loaded from secure storage")
            return api_key
        
        # Check for api.txt in current directory (legacy support)
        if os.path.exists('api.txt'):
            try:
                with open('api.txt', 'r', encoding='utf-8') as f:
                    api_key = f.read().strip()
                    if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE" and len(api_key) > 10:
                        print("[OK] API key loaded from api.txt")
                        # Save it securely
                        self.api_manager.save_key(api_key)
                        return api_key
            except:
                pass
        
        # Check if there's a bundled api.txt
        bundled_api = get_resource_path('api.txt')
        if os.path.exists(bundled_api) and bundled_api != 'api.txt':
            try:
                with open(bundled_api, 'r', encoding='utf-8') as f:
                    api_key = f.read().strip()
                    if api_key and api_key != "YOUR_GEMINI_API_KEY_HERE" and len(api_key) > 10:
                        print("[OK] API key loaded from bundled file")
                        # Save it securely
                        self.api_manager.save_key(api_key)
                        return api_key
            except:
                pass
        
        print("[INFO] No API key found. User must set it in settings.")
        return None

    def save_api_key(self, api_key):
        """Save API key and reinitialize Gemini"""
        try:
            # Validate API key
            if not api_key or len(api_key) < 10:
                print("[ERROR] Invalid API key format")
                return False
            
            # Save using manager
            if self.api_manager.save_key(api_key):
                print("[OK] API key saved securely")
                
                # Reinitialize Gemini
                if api_key != self.current_api_key:
                    print("[INFO] Reinitializing Gemini with new key...")
                    if self.initialize_gemini(api_key):
                        self.safe_update_text("✅ API key updated successfully!")
                        self.update_api_status_display()
                        return True
                    else:
                        self.safe_update_text("❌ Failed to initialize with new key")
                        return False
                return True
            
            return False
            
        except Exception as e:
            print(f"[ERROR] Could not save API key: {e}")
            return False

    def initialize_gemini(self, api_key):
        """Initialize Gemini provider"""
        try:
            print(f"[GEMINI] Initializing with key: {api_key[:10]}...")
            self.current_api_key = api_key
            
            # Reset request counter on new initialization
            self.request_count = 0
            self.last_request_reset = time.time()
            
            self.gemini = SimpleGeminiProvider(api_key)
            
            # Set prompt if available
            prompt = self.get_prompt()
            if hasattr(self.gemini, 'prompt'):
                self.gemini.prompt = prompt
            
            print("[OK] Gemini provider initialized")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini: {e}")
            self.gemini = None
            self.current_api_key = None
            return False

    def get_prompt(self):
        """Get prompt text"""
        # Check bundled prompt
        bundled_prompt = get_resource_path('prompt.txt')
        if os.path.exists(bundled_prompt):
            try:
                with open(bundled_prompt, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except:
                pass
        
        # Check local prompt
        if os.path.exists('prompt.txt'):
            try:
                with open('prompt.txt', 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except:
                pass
        
        # Default prompt
        return """Analyze this nursing exam question.
For 'Select all that apply': identify ALL correct options.
For single answer: provide the correct choice.
Be direct and clear with your answer."""

    def load_hotkey_settings(self):
        """Load hotkey settings"""
        self.hotkeys = {
            'add_screenshot': {'keys': ['ctrl', 'alt', 'a'], 'display': 'Ctrl+Alt+A'},
            'analyze_multiple': {'keys': ['ctrl', 'alt', 'm'], 'display': 'Ctrl+Alt+M'},
            'clear_all': {'keys': ['ctrl', 'alt', 'c'], 'display': 'Ctrl+Alt+C'},
            'settings': {'keys': ['ctrl', 'alt', 's'], 'display': 'Ctrl+Alt+S'},
            'update': {'keys': ['ctrl', 'alt', 'u'], 'display': 'Ctrl+Alt+U'},
            'exit': {'keys': ['ctrl', 'alt', 'x'], 'display': 'Ctrl+Alt+X'}
        }
        
        # Try to load saved settings
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    if 'hotkeys' in settings:
                        for key, combo in settings['hotkeys'].items():
                            if combo and key in self.hotkeys:
                                parts = combo.lower().replace('+', ' ').split()
                                self.hotkeys[key] = {'keys': parts, 'display': combo}
        except:
            pass

    def save_settings(self, settings):
        """Save settings"""
        try:
            # Update screenshot setting if present
            if 'save_screenshots' in settings:
                self.capture.enable_screenshots(settings['save_screenshots'])
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            print("[OK] Settings saved")
        except Exception as e:
            print(f"[ERROR] Could not save settings: {e}")

    def update_hotkeys(self, new_hotkeys):
        """Update hotkeys"""
        for key, combo in new_hotkeys.items():
            if combo and key in self.hotkeys:
                parts = combo.lower().replace('+', ' ').split()
                self.hotkeys[key] = {'keys': parts, 'display': combo}
        self.print_controls()

    def print_controls(self):
        """Print controls"""
        print("\n" + "="*50)
        print("CONTROLS:")
        print("-"*50)
        print("  Right-click hold 2s : Capture & Analyze")
        print(f"  {self.hotkeys['add_screenshot']['display']:<15} : Add screenshot")
        print(f"  {self.hotkeys['analyze_multiple']['display']:<15} : Analyze all")
        print(f"  {self.hotkeys['clear_all']['display']:<15} : Clear screenshots")
        print(f"  {self.hotkeys['settings']['display']:<15} : Settings")
        print(f"  {self.hotkeys['update']['display']:<15} : Check for updates")
        print(f"  {self.hotkeys['exit']['display']:<15} : Exit")
        print("="*50)

    def check_for_updates_manual(self):
        """Manual update check triggered by user"""
        self.safe_update_text("🔍 Checking for updates...")
        
        def update_thread():
            try:
                # Check for updates
                success, message = self.updater.check_and_update(auto_apply=False)
                
                if success and "available" in message.lower():
                    # Get detailed update info
                    manifest = self.updater.fetch_dynamic_manifest()
                    
                    if manifest:
                        version = manifest.get('version', 'new')
                        changelog = manifest.get('changelog', 'Bug fixes and improvements')
                        update_type = manifest.get('update_requirements', {}).get('update_type', 'hot_reload')
                        file_count = len(manifest.get('structure', {}))
                        size_mb = manifest.get('statistics', {}).get('total_size_mb', 0)
                        
                        # Show update details
                        update_msg = f"🎉 Update {version} Available!\n"
                        update_msg += f"📦 {file_count} files ({size_mb:.1f} MB)\n"
                        update_msg += f"🔄 Type: {update_type.replace('_', ' ').title()}\n"
                        update_msg += f"📝 {changelog[:100]}..."
                        
                        self.safe_update_text(update_msg)
                        
                        # Wait for user to see the message
                        time.sleep(3)
                        
                        # Apply update
                        self.safe_update_text(f"📥 Installing update {version}...")
                        success, result_msg = self.updater.check_and_update(auto_apply=True)
                        
                        if success:
                            if "restart" in result_msg.lower():
                                self.safe_update_text(f"✅ Update complete!\n🔄 Restarting...")
                                time.sleep(2)
                                self.restart_application()
                            else:
                                self.safe_update_text(f"✅ Updated to {version}!\nNo restart needed.")
                                # Update version in memory
                                global APP_VERSION
                                APP_VERSION = version
                        else:
                            self.safe_update_text(f"❌ Update failed:\n{result_msg}")
                    else:
                        self.safe_update_text("❌ Could not fetch update details")
                else:
                    self.safe_update_text(f"✅ {message}")
                    
            except Exception as e:
                self.safe_update_text(f"❌ Update check failed:\n{str(e)[:100]}")
                print(f"[ERROR] Update check failed: {e}")
                traceback.print_exc()
        
        threading.Thread(target=update_thread, daemon=True).start()

    def restart_application(self):
        """Restart the application after update"""
        try:
            # Save current state if needed
            if hasattr(self, 'settings_file'):
                self.save_settings({
                    'last_restart': datetime.now().isoformat(),
                    'version': APP_VERSION
                })
            
            # Determine how we're running
            if getattr(sys, 'frozen', False):
                # Running as compiled EXE
                executable = sys.executable
                subprocess.Popen([executable])
            else:
                # Running as Python script
                python = sys.executable
                script = sys.argv[0]
                subprocess.Popen([python, script])
            
            # Exit current instance
            self.running = False
            os._exit(0)
            
        except Exception as e:
            print(f"[ERROR] Could not restart: {e}")
            self.safe_update_text("❌ Auto-restart failed.\nPlease restart manually.")

    def check_rate_limit(self):
        """Check if we're approaching rate limits"""
        # Reset counter every hour
        if time.time() - self.last_request_reset > 3600:
            self.request_count = 0
            self.last_request_reset = time.time()
        
        self.request_count += 1
        
        # Warn if approaching limits
        if self.request_count > 50:
            print(f"[WARNING] High request count: {self.request_count} requests this hour")
            # Add delay to prevent rate limiting
            time.sleep(2)
        elif self.request_count > 30:
            time.sleep(1)

    def safe_update_text(self, text):
        """Queue text update"""
        self.update_queue.put(("text", text))

    def safe_update_capture_status(self, text):
        """Queue status update"""
        self.update_queue.put(("capture_status", text))

    def process_updates(self):
        """Process queued updates"""
        try:
            while not self.update_queue.empty():
                item = self.update_queue.get_nowait()
                
                if isinstance(item, tuple) and len(item) == 2:
                    update_type, text = item
                    
                    if hasattr(self.overlay, 'update_capture_status') and update_type == "capture_status":
                        self.overlay.update_capture_status(text)
                    elif hasattr(self.overlay, 'open_settings') and update_type == "settings":
                        self.overlay.open_settings()
                    elif hasattr(self.overlay, 'update_text'):
                        self.overlay.update_text(text)
        except:
            pass

    def setup_mouse_listener(self):
        """Setup mouse listener"""
        def on_click(x, y, button, pressed):
            if button == mouse.Button.right:
                if pressed:
                    self.right_click_start = time.time()
                    self.right_click_held = True
                    threading.Thread(target=self._check_right_click_hold, daemon=True).start()
                else:
                    self.right_click_held = False
                    self.right_click_start = None
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()

    def _check_right_click_hold(self):
        """Check right click hold"""
        start_time = self.right_click_start
        
        # Countdown messages
        messages = [
            (0.5, "CAPTURE → Holding... 2.0s"),
            (0.5, "CAPTURE → Holding... 1.5s"),
            (0.5, "CAPTURE → Holding... 1.0s"),
            (0.5, "CAPTURE → Ready... 0.5s")
        ]
        
        for delay, message in messages:
            if not self.right_click_held or self.right_click_start != start_time:
                self.safe_update_capture_status("CAPTURE → Hold right mouse button (2 sec)")
                return
            
            self.safe_update_capture_status(message)
            time.sleep(delay)
        
        if self.right_click_held and self.right_click_start == start_time:
            self.safe_update_capture_status("CAPTURE → Capturing now!")
            self.safe_update_text("[Capturing...]")
            self.quick_capture_analyze()
            time.sleep(0.5)
            self.safe_update_capture_status("CAPTURE → Hold right mouse button (2 sec)")
            self.right_click_held = False

    def setup_hotkeys(self):
        """Setup keyboard hotkeys"""
        self.current_keys = set()
        
        def on_press(key):
            # Don't process if settings dialog is open
            try:
                if hasattr(self.overlay, 'settings_dialog_open') and self.overlay.settings_dialog_open:
                    return
            except:
                pass
            
            self.current_keys.add(key)
            
            # Check for Ctrl and Alt
            ctrl = any(k in self.current_keys for k in [keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.ctrl])
            alt = any(k in self.current_keys for k in [keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt])
            
            if ctrl and alt:
                char = None
                if hasattr(key, 'char') and key.char:
                    char = key.char.lower()
                elif hasattr(key, 'vk'):
                    # Virtual key codes
                    vk_map = {
                        65: 'a',  # A
                        77: 'm',  # M
                        67: 'c',  # C
                        83: 's',  # S
                        85: 'u',  # U
                        88: 'x'   # X
                    }
                    char = vk_map.get(key.vk)
                
                # Handle hotkeys
                if char == 'a' and not self.is_analyzing:
                    self.add_screenshot()
                elif char == 'm' and not self.is_analyzing:
                    self.analyze_multiple()
                elif char == 'c':
                    self.clear_screenshots()
                elif char == 's':
                    self.open_settings()
                elif char == 'u':
                    self.check_for_updates_manual()
                elif char == 'x':
                    self.running = False
        
        def on_release(key):
            self.current_keys.discard(key)
        
        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

    def quick_capture_analyze(self):
        """Quick capture and analyze"""
        threading.Thread(target=self._quick_capture_analyze_thread, daemon=False).start()

    def _quick_capture_analyze_thread(self):
        """Capture and analyze thread"""
        self.is_analyzing = True
        
        try:
            if not self.gemini:
                self.safe_update_text("❌ Please set API key!\nPress Ctrl+Alt+S")
                return
            
            # Check rate limit
            self.check_rate_limit()
            
            # Capture screen
            result, result_type = self.capture.capture_or_extract()
            
            if result_type == 'image':
                # Convert to bytes
                img_byte_arr = io.BytesIO()
                result.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                self.safe_update_text("[Getting Answer...]")
                self.safe_update_capture_status("CAPTURE → Getting Answer...")
                
                # Analyze with Gemini
                answer = self.gemini.analyze_image(img_bytes)
                
                # Check for rate limit or error messages
                if "rate limit" in answer.lower() or "quota" in answer.lower():
                    print(f"[WARNING] Rate limit detected. Requests this hour: {self.request_count}")
                    self.safe_update_text("⏳ Rate limited. Please wait a moment and try again.")
                else:
                    self.safe_update_text(answer)
                    
            elif result_type == 'text':
                self.safe_update_text("[Getting Answer...]")
                answer = self.gemini.analyze_text(result)
                self.safe_update_text(answer)
            else:
                self.safe_update_text("❌ Capture failed")
                
        except Exception as e:
            self.safe_update_text(f"❌ Error: {str(e)[:50]}")
            print(f"[ERROR] Analysis failed: {e}")
        finally:
            self.is_analyzing = False
            self.safe_update_capture_status("CAPTURE → Hold right mouse button (2 sec)")

    def add_screenshot(self):
        """Add screenshot to collection"""
        threading.Thread(target=self._add_screenshot_thread, daemon=False).start()

    def _add_screenshot_thread(self):
        """Add screenshot thread"""
        try:
            result, result_type = self.capture.capture_or_extract()
            if result_type == 'image':
                self.screenshot_collection.append(result)
                count = len(self.screenshot_collection)
                self.safe_update_text(f"📸 Screenshot {count} added\nTotal saved: {count}\nPress {self.hotkeys['analyze_multiple']['display']} to analyze all")
            else:
                self.safe_update_text("❌ Capture failed")
        except Exception as e:
            self.safe_update_text(f"❌ Error: {str(e)[:50]}")

    def analyze_multiple(self):
        """Analyze multiple screenshots"""
        threading.Thread(target=self._analyze_multiple_thread, daemon=False).start()

    def _analyze_multiple_thread(self):
        """Thread for analyzing multiple screenshots"""
        self.is_analyzing = True
        
        try:
            if not self.gemini:
                self.safe_update_text("❌ Please set your API key first!\nPress Ctrl+Alt+S for settings")
                return
                
            if not self.screenshot_collection:
                self.safe_update_text("📸 No screenshots collected\nPress Ctrl+Alt+A to add")
                return
            
            # Check rate limit
            self.check_rate_limit()
            
            # Show preparing message
            self.safe_update_text(f"[Preparing {len(self.screenshot_collection)} screenshots...]")
            
            # Convert all images to bytes
            all_images = []
            for img in self.screenshot_collection:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                all_images.append(img_byte_arr.getvalue())
            
            # Show getting answer message
            self.safe_update_text("[Getting Answer...]")
            
            try:
                if len(all_images) == 1:
                    answer = self.gemini.analyze_image(all_images[0])
                else:
                    answer = self.gemini.analyze_multiple_images(all_images)
                
                # Check for rate limit or error messages
                if "rate limit" in answer.lower() or "quota" in answer.lower():
                    print(f"[WARNING] Rate limit detected. Requests this hour: {self.request_count}")
                    self.safe_update_text("⏳ Rate limited. Please wait a moment and try again.")
                elif answer and "Unable to" not in answer and "Error" not in answer:
                    self.safe_update_text(answer)
                else:
                    self.safe_update_text("❌ API Error. Check your API key in settings (Ctrl+Alt+S)")
                    
            except Exception as e:
                print(f"[ERROR] Multiple image analysis failed: {e}")
                self.safe_update_text("❌ Analysis failed. Check API key in settings.")
            
            # Clear collection after analysis
            self.screenshot_collection = []
            
        except Exception as e:
            self.safe_update_text(f"❌ Error: {str(e)[:50]}")
            
        finally:
            self.is_analyzing = False

    def open_settings(self):
        """Open settings dialog"""
        if hasattr(self.overlay, 'open_settings'):
            self.update_queue.put(("settings", "open"))

    def clear_screenshots(self):
        """Clear screenshot collection"""
        self.screenshot_collection = []
        self.safe_update_text("🗑️ Screenshots cleared")

    def run(self):
        """Main application loop"""
        try:
            # Show overlay
            if self.overlay:
                self.overlay.show()
            
            # Main loop
            while self.running:
                # Process UI updates
                self.process_updates()
                
                # Process Qt events if available
                try:
                    if hasattr(self.overlay, 'app') and self.overlay.app:
                        self.overlay.app.processEvents()
                        if self.overlay.visible:
                            self.overlay.raise_()
                except:
                    pass
                
                # Small delay to prevent CPU spinning
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n[INFO] Shutting down (user interrupt)...")
        except Exception as e:
            print(f"[ERROR] Runtime error: {e}")
            traceback.print_exc()
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        print("\n" + "="*50)
        print("SHUTTING DOWN...")
        print("-"*50)
        
        self.running = False
        
        # Stop listeners
        try:
            if hasattr(self, 'listener'):
                self.listener.stop()
                print("[OK] Keyboard listener stopped")
        except:
            pass
        
        try:
            if hasattr(self, 'mouse_listener'):
                self.mouse_listener.stop()
                print("[OK] Mouse listener stopped")
        except:
            pass
        
        # Close UI
        try:
            if hasattr(self.overlay, 'app') and self.overlay.app:
                self.overlay.app.quit()
                print("[OK] UI closed")
        except:
            pass
        
        # Cleanup capture system
        try:
            if hasattr(self, 'capture'):
                self.capture.cleanup()
                print("[OK] Capture system cleaned up")
        except:
            pass
        
        print("="*50)
        print("Goodbye! Thank you for using GoStealthAI")
        sys.exit(0)


def main():
    """Main entry point"""
    try:
        # Check if running as admin (Windows)
        if sys.platform == 'win32':
            try:
                import ctypes
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                if not is_admin:
                    print("\n" + "!"*50)
                    print("WARNING: Not running as Administrator!")
                    print("Some features may not work properly.")
                    print("For best results, run as Administrator.")
                    print("!"*50 + "\n")
            except:
                pass
        
        # Create and run application
        app = GoStealthAISimple()
        app.run()
        
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
