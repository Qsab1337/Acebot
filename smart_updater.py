"""
Smart Auto-Updater for GoStealthAI
GitHub-based, hot-reload capable, zero-downtime updates
"""
import os
import sys
import json
import time
import requests
import subprocess
import hashlib
import threading
import shutil
import tempfile
import importlib
from datetime import datetime
from packaging import version


class SmartUpdater:
    def __init__(self, app_instance=None, current_version="1.0.1"):
        """Initialize the smart updater"""
        self.app = app_instance
        self.current_version = current_version
        
        # GitHub Configuration
        self.github_user = "Qsab1337"
        self.github_repo = "Acebot"
        self.branch = "main"
        
        # URLs
        self.base_url = f"https://raw.githubusercontent.com/{self.github_user}/{self.github_repo}/{self.branch}"
        self.releases_url = f"https://api.github.com/repos/{self.github_user}/{self.github_repo}/releases/latest"
        self.manifest_url = f"{self.base_url}/update_manifest.json"
        
        # Paths
        self.app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.backup_dir = os.path.join(self.app_dir, "backup")
        self.temp_dir = os.path.join(self.app_dir, "temp_update")
        
        # Create directories
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Update state
        self.update_available = False
        self.update_info = {}
        self.is_updating = False
        self.update_progress = 0
        
        # Modules that can be hot-reloaded
        self.hot_reloadable = [
            'simple_gemini_provider',
            'simple_ocr',
            'advanced_capture',
            'ui_automation_capture'
        ]
        
        # Modules that require restart
        self.restart_required = [
            'main_simple',
            'overlay_windows'
        ]
        
        print(f"[SmartUpdater] Initialized - Version {self.current_version}")
        print(f"[SmartUpdater] Checking: {self.github_user}/{self.github_repo}")
    
    def check_for_updates(self, silent=True):
        """Check GitHub for updates"""
        try:
            if not silent:
                print("[SmartUpdater] Checking for updates...")
            
            # Try to get manifest first (faster)
            try:
                response = requests.get(self.manifest_url, timeout=3)
                if response.status_code == 200:
                    manifest = response.json()
                    remote_version = manifest.get('version', '0.0.0')
                    
                    # Compare versions
                    if version.parse(remote_version) > version.parse(self.current_version):
                        self.update_available = True
                        self.update_info = manifest
                        
                        if not silent:
                            print(f"[SmartUpdater] Update available: {self.current_version} → {remote_version}")
                        
                        return True, manifest
                    else:
                        if not silent:
                            print(f"[SmartUpdater] Already on latest version {self.current_version}")
                        return False, None
            except:
                pass
            
            # Fallback: Check releases API
            response = requests.get(self.releases_url, timeout=5)
            if response.status_code == 200:
                release_data = response.json()
                remote_version = release_data.get('tag_name', '0.0.0').replace('v', '')
                
                if version.parse(remote_version) > version.parse(self.current_version):
                    self.update_available = True
                    self.update_info = {
                        'version': remote_version,
                        'changelog': release_data.get('body', 'Bug fixes and improvements'),
                        'type': self._determine_update_type(remote_version),
                        'download_url': None,
                        'files': []
                    }
                    
                    # Find EXE in assets
                    for asset in release_data.get('assets', []):
                        if asset['name'].endswith('.exe'):
                            self.update_info['download_url'] = asset['browser_download_url']
                            break
                    
                    if not silent:
                        print(f"[SmartUpdater] Update available: {self.current_version} → {remote_version}")
                    
                    return True, self.update_info
            
            return False, None
            
        except requests.exceptions.ConnectionError:
            if not silent:
                print("[SmartUpdater] No internet connection")
            return False, None
        except Exception as e:
            if not silent:
                print(f"[SmartUpdater] Check failed: {e}")
            return False, None
    
    def _determine_update_type(self, new_version):
        """Determine if update is major, minor, or patch"""
        current = version.parse(self.current_version)
        new = version.parse(new_version)
        
        if new.major > current.major:
            return 'major'
        elif new.minor > current.minor:
            return 'minor'
        else:
            return 'patch'
    
    def download_file(self, url, destination, show_progress=False):
        """Download file with progress and resume support"""
        try:
            # Check if partial download exists
            temp_file = f"{destination}.download"
            resume_header = {}
            
            if os.path.exists(temp_file):
                resume_header = {'Range': f'bytes={os.path.getsize(temp_file)}-'}
            
            response = requests.get(url, headers=resume_header, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            
            # Write mode based on resume
            mode = 'ab' if resume_header else 'wb'
            
            with open(temp_file, mode) as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if show_progress and total_size > 0:
                            self.update_progress = int((downloaded / total_size) * 100)
                            if self.app:
                                self.app.safe_update_text(f"Downloading update... {self.update_progress}%")
            
            # Move completed download
            shutil.move(temp_file, destination)
            return True
            
        except Exception as e:
            print(f"[SmartUpdater] Download failed: {e}")
            return False
    
    def verify_file(self, file_path, expected_hash=None):
        """Verify file integrity"""
        if not os.path.exists(file_path):
            return False
        
        if expected_hash:
            sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            
            return sha256.hexdigest() == expected_hash
        
        # If no hash provided, just check file exists and is not empty
        return os.path.getsize(file_path) > 0
    
    def backup_current_version(self):
        """Backup current files before update"""
        try:
            backup_path = os.path.join(self.backup_dir, f"v{self.current_version}_{int(time.time())}")
            os.makedirs(backup_path, exist_ok=True)
            
            # Backup Python files
            for file in os.listdir(self.app_dir):
                if file.endswith('.py') or file.endswith('.exe'):
                    src = os.path.join(self.app_dir, file)
                    dst = os.path.join(backup_path, file)
                    if os.path.exists(src):
                        shutil.copy2(src, dst)
            
            print(f"[SmartUpdater] Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"[SmartUpdater] Backup failed: {e}")
            return None
    
    def hot_reload_module(self, module_name):
        """Hot reload a Python module"""
        try:
            if module_name in sys.modules:
                # Save state if needed
                old_module = sys.modules[module_name]
                
                # Reload the module
                importlib.reload(sys.modules[module_name])
                
                # Reinitialize in app if needed
                if self.app and module_name == 'simple_gemini_provider':
                    if hasattr(self.app, 'current_api_key') and self.app.current_api_key:
                        from simple_gemini_provider import SimpleGeminiProvider
                        self.app.gemini = SimpleGeminiProvider(self.app.current_api_key)
                
                print(f"[SmartUpdater] Hot-reloaded: {module_name}")
                return True
            
            return False
            
        except Exception as e:
            print(f"[SmartUpdater] Hot-reload failed for {module_name}: {e}")
            return False
    
    def update_python_files(self, files_list):
        """Update Python files and hot-reload where possible"""
        updated_files = []
        restart_needed = False
        
        for file_info in files_list:
            try:
                file_name = file_info['name']
                file_url = file_info.get('url', f"{self.base_url}/{file_name}")
                
                # Download to temp first
                temp_path = os.path.join(self.temp_dir, file_name)
                if self.download_file(file_url, temp_path):
                    # Verify if hash provided
                    if 'sha256' in file_info:
                        if not self.verify_file(temp_path, file_info['sha256']):
                            print(f"[SmartUpdater] Verification failed: {file_name}")
                            continue
                    
                    # Move to app directory
                    final_path = os.path.join(self.app_dir, file_name)
                    shutil.move(temp_path, final_path)
                    updated_files.append(file_name)
                    
                    # Try hot reload
                    module_name = file_name.replace('.py', '')
                    if module_name in self.hot_reloadable:
                        if not self.hot_reload_module(module_name):
                            restart_needed = True
                    elif module_name in self.restart_required:
                        restart_needed = True
                    
            except Exception as e:
                print(f"[SmartUpdater] Failed to update {file_name}: {e}")
        
        return updated_files, restart_needed
    
    def update_exe(self, download_url=None):
        """Update the EXE file"""
        try:
            if not download_url:
                download_url = self.update_info.get('download_url')
            
            if not download_url:
                print("[SmartUpdater] No EXE download URL")
                return False
            
            # Get current EXE path
            if getattr(sys, 'frozen', False):
                current_exe = sys.executable
            else:
                # Running from Python, look for EXE
                current_exe = os.path.join(self.app_dir, "GoStealthAI.exe")
                if not os.path.exists(current_exe):
                    print("[SmartUpdater] Not running from EXE")
                    return False
            
            # Download new EXE
            new_exe = current_exe + ".new"
            print(f"[SmartUpdater] Downloading new EXE...")
            
            if not self.download_file(download_url, new_exe, show_progress=True):
                return False
            
            # Create update script
            update_script = os.path.join(self.app_dir, "apply_update.bat")
            script_content = f'''@echo off
echo Applying update...
timeout /t 3 /nobreak > nul
taskkill /f /im "{os.path.basename(current_exe)}" 2>nul
timeout /t 1 /nobreak > nul
move /y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
'''
            
            with open(update_script, 'w') as f:
                f.write(script_content)
            
            print("[SmartUpdater] Launching update script...")
            
            # Launch update script
            subprocess.Popen(
                update_script,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            )
            
            # Exit current app
            if self.app:
                self.app.safe_update_text("Restarting with update...")
            
            time.sleep(1)
            os._exit(0)
            
        except Exception as e:
            print(f"[SmartUpdater] EXE update failed: {e}")
            return False
    
    def apply_update(self, auto_mode=False):
        """Apply the update based on type"""
        if not self.update_available or not self.update_info:
            return False
        
        self.is_updating = True
        
        try:
            # Backup current version
            backup_path = self.backup_current_version()
            
            update_type = self.update_info.get('type', 'patch')
            
            if update_type in ['patch', 'minor']:
                # Try hot reload first
                files = self.update_info.get('files', [])
                if files:
                    updated, restart_needed = self.update_python_files(files)
                    
                    if updated and not restart_needed:
                        # Success with hot reload
                        if self.app:
                            self.app.safe_update_text(f"✅ Updated to v{self.update_info['version']} (no restart)")
                        self.current_version = self.update_info['version']
                        self.save_version()
                        return True
                    elif updated and restart_needed:
                        # Need restart
                        if auto_mode:
                            return self.update_exe()
                        else:
                            if self.app:
                                self.app.safe_update_text(f"✅ Update ready. Restart to apply v{self.update_info['version']}")
                            return True
            
            # Major update - need EXE replacement
            if update_type == 'major' or self.update_info.get('download_url'):
                return self.update_exe()
            
            return False
            
        except Exception as e:
            print(f"[SmartUpdater] Update failed: {e}")
            # Rollback if needed
            if backup_path:
                self.rollback(backup_path)
            return False
        finally:
            self.is_updating = False
    
    def rollback(self, backup_path):
        """Rollback to previous version"""
        try:
            print(f"[SmartUpdater] Rolling back from {backup_path}")
            
            # Restore files
            for file in os.listdir(backup_path):
                src = os.path.join(backup_path, file)
                dst = os.path.join(self.app_dir, file)
                shutil.copy2(src, dst)
            
            print("[SmartUpdater] Rollback complete")
            return True
            
        except Exception as e:
            print(f"[SmartUpdater] Rollback failed: {e}")
            return False
    
    def save_version(self):
        """Save current version to file"""
        try:
            version_file = os.path.join(self.app_dir, "version.json")
            with open(version_file, 'w') as f:
                json.dump({
                    'version': self.current_version,
                    'updated': datetime.now().isoformat()
                }, f)
        except:
            pass
    
    def auto_update_check(self):
        """Run update check in background"""
        def check_thread():
            try:
                has_update, info = self.check_for_updates(silent=True)
                if has_update and self.app:
                    # Notify user
                    version = info.get('version', 'new')
                    self.app.safe_update_text(f"🎉 Update {version} available! Installing...")
                    
                    # Auto apply if it's a patch
                    if info.get('type') == 'patch':
                        time.sleep(2)  # Give user time to see message
                        self.apply_update(auto_mode=True)
                    else:
                        self.app.safe_update_text(f"🎉 Update {version} ready! Restart when convenient.")
            except:
                pass
        
        # Start background thread
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()


# Standalone update check function
def check_and_update(current_version="1.0.1"):
    """Standalone function to check and apply updates"""
    updater = SmartUpdater(current_version=current_version)
    
    print("\n" + "="*50)
    print("GoStealthAI Update Check")
    print("="*50)
    
    has_update, info = updater.check_for_updates(silent=False)
    
    if has_update:
        print(f"\n📦 Update available: v{info['version']}")
        print(f"Type: {info.get('type', 'patch').upper()}")
        print(f"Changes: {info.get('changelog', 'Bug fixes and improvements')[:100]}...")
        
        response = input("\nApply update now? (y/n): ")
        if response.lower() == 'y':
            if updater.apply_update():
                print("✅ Update applied successfully!")
            else:
                print("❌ Update failed")
    else:
        print("✅ You're on the latest version!")
    
    print("="*50)


if __name__ == "__main__":
    # Test the updater
    check_and_update()
