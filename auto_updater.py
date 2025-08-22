"""
Enhanced Auto-Updater with Hot-Reload
Automatically updates and restarts without user intervention
"""
import os
import sys
import json
import time
import requests
import subprocess
import hashlib
import threading
from datetime import datetime
from packaging import version


class AutoUpdater:
    def __init__(self, current_version="1.0.0", ui_callback=None):
        self.github_user = "Qsab1337"
        self.github_repo = "Acebot"
        self.current_version = current_version
        self.ui_callback = ui_callback
        
        # URLs
        self.version_url = f"https://raw.githubusercontent.com/{self.github_user}/{self.github_repo}/main/version.txt"
        self.releases_api = f"https://api.github.com/repos/{self.github_user}/{self.github_repo}/releases/latest"
        
        # Paths
        self.exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        self.exe_dir = os.path.dirname(os.path.abspath(self.exe_path))
        self.exe_name = os.path.basename(self.exe_path)
        
        # Update files
        self.new_exe = os.path.join(self.exe_dir, f"{self.exe_name}.new")
        self.backup_exe = os.path.join(self.exe_dir, f"{self.exe_name}.backup")
        self.updater_script = os.path.join(self.exe_dir, "update.bat")
        
        # Update info
        self.update_available = False
        self.update_info = {}
        self.download_progress = 0
        
        print(f"[AutoUpdater] Current version: {self.current_version}")
        print(f"[AutoUpdater] EXE location: {self.exe_path}")
    
    def notify(self, message):
        """Send status updates to UI"""
        print(f"[AutoUpdater] {message}")
        if self.ui_callback:
            try:
                self.ui_callback(message)
            except:
                pass
    
    def check_for_updates(self):
        """Check GitHub for new version"""
        try:
            self.notify("Checking for updates...")
            
            # Get latest version from GitHub
            response = requests.get(self.version_url, timeout=3)
            if response.status_code == 200:
                remote_version = response.text.strip()
                
                # Compare versions
                if version.parse(remote_version) > version.parse(self.current_version):
                    self.update_available = True
                    self.update_info['version'] = remote_version
                    
                    # Get release details
                    try:
                        release_response = requests.get(self.releases_api, timeout=5)
                        if release_response.status_code == 200:
                            release_data = release_response.json()
                            
                            # Find EXE asset
                            for asset in release_data.get('assets', []):
                                if asset['name'].endswith('.exe'):
                                    self.update_info['download_url'] = asset['browser_download_url']
                                    self.update_info['size'] = asset['size']
                                    self.update_info['sha256'] = asset.get('sha256', '')
                                    break
                            
                            # Get changelog
                            self.update_info['changelog'] = release_data.get('body', 'Bug fixes and improvements')
                    except:
                        # Construct download URL if API fails
                        self.update_info['download_url'] = f"https://github.com/{self.github_user}/{self.github_repo}/releases/latest/download/GoStealthAI.exe"
                    
                    size_mb = self.update_info.get('size', 0) / (1024 * 1024)
                    self.notify(f"🎉 New version {remote_version} available! ({size_mb:.1f} MB)")
                    return True
                else:
                    self.notify("✅ You have the latest version!")
                    return False
            
        except requests.exceptions.ConnectionError:
            self.notify("📡 No internet connection")
        except Exception as e:
            self.notify(f"❌ Update check failed: {str(e)[:50]}")
        
        return False
    
    def download_update_with_progress(self):
        """Download update with progress reporting"""
        try:
            if not self.update_info.get('download_url'):
                # Build default URL
                self.update_info['download_url'] = f"https://github.com/{self.github_user}/{self.github_repo}/releases/latest/download/GoStealthAI.exe"
            
            url = self.update_info['download_url']
            self.notify(f"📥 Downloading version {self.update_info.get('version', 'latest')}...")
            
            # Download with progress
            response = requests.get(url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            
            downloaded = 0
            chunk_size = 8192
            
            with open(self.new_exe, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            self.download_progress = int((downloaded / total_size) * 100)
                            
                            # Update UI every 10%
                            if self.download_progress % 10 == 0:
                                mb_down = downloaded / (1024 * 1024)
                                mb_total = total_size / (1024 * 1024)
                                self.notify(f"📊 Downloading... {self.download_progress}% ({mb_down:.1f}/{mb_total:.1f} MB)")
            
            self.notify("✅ Download complete!")
            return True
            
        except Exception as e:
            self.notify(f"❌ Download failed: {str(e)[:50]}")
            if os.path.exists(self.new_exe):
                try:
                    os.remove(self.new_exe)
                except:
                    pass
            return False
    
    def create_update_script(self):
        """Create batch script to replace EXE and restart"""
        script_content = f'''@echo off
echo Applying update...
timeout /t 2 /nobreak > nul

REM Kill the old process if still running
taskkill /f /im "{self.exe_name}" 2>nul
timeout /t 1 /nobreak > nul

REM Backup current EXE
if exist "{self.exe_path}" (
    move /y "{self.exe_path}" "{self.backup_exe}" > nul 2>&1
)

REM Apply new EXE
move /y "{self.new_exe}" "{self.exe_path}" > nul 2>&1

REM Start updated EXE
start "" "{self.exe_path}"

REM Clean up
timeout /t 2 /nobreak > nul
del "%~f0"
'''
        
        try:
            with open(self.updater_script, 'w') as f:
                f.write(script_content)
            return True
        except Exception as e:
            self.notify(f"❌ Could not create update script: {e}")
            return False
    
    def apply_update_hot_reload(self):
        """Apply update without requiring manual restart"""
        try:
            if not os.path.exists(self.new_exe):
                self.notify("❌ Update file not found")
                return False
            
            self.notify("🔄 Installing update...")
            
            # Create update script
            if not self.create_update_script():
                return False
            
            # Launch updater script
            self.notify("🚀 Restarting with new version...")
            
            # Start the update script
            subprocess.Popen(
                [self.updater_script],
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            )
            
            # Wait a moment for script to start
            time.sleep(1)
            
            # Exit current process
            self.notify("Closing current version...")
            os._exit(0)  # Force exit to allow replacement
            
        except Exception as e:
            self.notify(f"❌ Update failed: {str(e)[:50]}")
            return False
    
    def auto_update_async(self, auto_install=True):
        """Complete auto-update process in background"""
        def update_thread():
            try:
                # Check for updates
                if self.check_for_updates():
                    
                    # Show what's new
                    if self.update_info.get('changelog'):
                        changes = self.update_info['changelog'][:200]
                        self.notify(f"📝 What's new: {changes}...")
                    
                    # Download update
                    if self.download_update_with_progress():
                        
                        if auto_install:
                            # Wait a bit for user to see the message
                            self.notify("✨ Update ready! Restarting in 5 seconds...")
                            time.sleep(5)
                            
                            # Apply update and restart
                            self.apply_update_hot_reload()
                        else:
                            self.notify("✅ Update downloaded! Restart to apply.")
                
            except Exception as e:
                self.notify(f"❌ Auto-update error: {str(e)[:50]}")
        
        # Start in background
        thread = threading.Thread(target=update_thread, daemon=True)
        thread.start()
    
    def rollback(self):
        """Rollback to previous version if update fails"""
        try:
            if os.path.exists(self.backup_exe):
                # Kill current process
                subprocess.run(['taskkill', '/f', '/im', self.exe_name], capture_output=True)
                time.sleep(1)
                
                # Restore backup
                if os.path.exists(self.exe_path):
                    os.remove(self.exe_path)
                os.rename(self.backup_exe, self.exe_path)
                
                # Restart
                subprocess.Popen([self.exe_path])
                
                self.notify("↩️ Rolled back to previous version")
                return True
                
        except Exception as e:
            self.notify(f"❌ Rollback failed: {e}")
        
        return False
