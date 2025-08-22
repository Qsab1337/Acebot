"""
Ultimate Dynamic Auto-Updater for GoStealthAI
Handles ANY changes - new files, deletions, complete restructuring
No need to ever update the updater itself!
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
import zipfile
import importlib
import importlib.util
from datetime import datetime
from pathlib import Path


class UltimateUpdater:
    def __init__(self, app_instance=None, current_version="1.0.0"):
        """Initialize the ultimate updater"""
        self.app = app_instance
        self.current_version = current_version
        
        # GitHub Configuration
        self.github_user = "Qsab1337"
        self.github_repo = "Acebot"
        self.branch = "main"
        
        # URLs
        self.base_url = f"https://raw.githubusercontent.com/{self.github_user}/{self.github_repo}/{self.branch}"
        self.api_base = f"https://api.github.com/repos/{self.github_user}/{self.github_repo}"
        
        # Dynamic manifest URL - this is the ONLY hardcoded URL
        self.manifest_url = f"{self.base_url}/update_system/manifest.json"
        
        # Paths
        self.app_dir = self._get_app_directory()
        self.backup_dir = os.path.join(self.app_dir, "_backups")
        self.temp_dir = os.path.join(self.app_dir, "_temp_update")
        self.update_cache = os.path.join(self.app_dir, "_update_cache")
        
        # Create directories
        for dir_path in [self.backup_dir, self.temp_dir, self.update_cache]:
            os.makedirs(dir_path, exist_ok=True)
        
        # Dynamic file tracking
        self.current_files = self._scan_current_installation()
        self.protected_files = ['ultimate_updater.py', '_backups', '_temp_update', '_update_cache']
        
        # Module management
        self.loaded_modules = {}
        self.module_versions = {}
        
        print(f"[UltimateUpdater] Initialized v{current_version}")
        print(f"[UltimateUpdater] Found {len(self.current_files)} files in installation")
    
    def _get_app_directory(self):
        """Get the actual app directory, whether running as EXE or Python"""
        if getattr(sys, 'frozen', False):
            # Running as compiled EXE
            return os.path.dirname(sys.executable)
        else:
            # Running as Python script
            return os.path.dirname(os.path.abspath(sys.argv[0]))
    
    def _scan_current_installation(self):
        """Scan and catalog all current files"""
        files = {}
        
        for root, dirs, filenames in os.walk(self.app_dir):
            # Skip protected directories
            dirs[:] = [d for d in dirs if not d.startswith('_')]
            
            for filename in filenames:
                if filename.startswith('_'):
                    continue
                    
                filepath = os.path.join(root, filename)
                relative_path = os.path.relpath(filepath, self.app_dir)
                
                # Calculate file hash
                file_hash = self._calculate_file_hash(filepath)
                file_size = os.path.getsize(filepath)
                
                files[relative_path] = {
                    'hash': file_hash,
                    'size': file_size,
                    'modified': os.path.getmtime(filepath)
                }
        
        return files
    
    def _calculate_file_hash(self, filepath):
        """Calculate SHA256 hash of a file"""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except:
            return None
    
    def fetch_dynamic_manifest(self):
        """Fetch the dynamic manifest that describes all available updates"""
        try:
            response = requests.get(self.manifest_url, timeout=5)
            if response.status_code == 200:
                manifest = response.json()
                
                # Validate manifest structure
                required_fields = ['version', 'structure', 'update_strategy']
                if all(field in manifest for field in required_fields):
                    return manifest
                else:
                    print("[UltimateUpdater] Invalid manifest structure")
                    return None
            return None
        except Exception as e:
            print(f"[UltimateUpdater] Failed to fetch manifest: {e}")
            return None
    
    def compare_versions(self, manifest):
        """Smart version comparison that handles any versioning scheme"""
        remote_version = manifest.get('version', '0.0.0')
        
        # Try semantic versioning first
        try:
            from packaging import version
            if version.parse(remote_version) > version.parse(self.current_version):
                return True, 'upgrade'
            elif version.parse(remote_version) < version.parse(self.current_version):
                return True, 'downgrade'
            else:
                return False, 'same'
        except:
            # Fallback to string comparison
            if remote_version != self.current_version:
                return True, 'different'
            return False, 'same'
    
    def analyze_update_requirements(self, manifest):
        """Analyze what needs to be updated based on manifest"""
        update_plan = {
            'add_files': [],
            'update_files': [],
            'delete_files': [],
            'add_directories': [],
            'delete_directories': [],
            'total_download_size': 0,
            'requires_restart': False,
            'update_type': 'hot_reload'  # hot_reload, soft_restart, hard_restart
        }
        
        # Get file structure from manifest
        remote_structure = manifest.get('structure', {})
        
        # Find files to add or update
        for file_path, file_info in remote_structure.items():
            local_file_path = os.path.join(self.app_dir, file_path)
            
            if file_path not in self.current_files:
                # New file
                update_plan['add_files'].append({
                    'path': file_path,
                    'url': file_info.get('url', f"{self.base_url}/{file_path}"),
                    'size': file_info.get('size', 0),
                    'hash': file_info.get('hash', ''),
                    'type': file_info.get('type', 'python')
                })
                update_plan['total_download_size'] += file_info.get('size', 0)
                
            elif self.current_files[file_path]['hash'] != file_info.get('hash', ''):
                # File exists but different
                update_plan['update_files'].append({
                    'path': file_path,
                    'url': file_info.get('url', f"{self.base_url}/{file_path}"),
                    'size': file_info.get('size', 0),
                    'hash': file_info.get('hash', ''),
                    'type': file_info.get('type', 'python')
                })
                update_plan['total_download_size'] += file_info.get('size', 0)
        
        # Find files to delete (exist locally but not in manifest)
        for local_file in self.current_files:
            if local_file not in remote_structure and local_file not in self.protected_files:
                update_plan['delete_files'].append(local_file)
        
        # Determine update type based on changes
        if any(f['path'].endswith('.exe') for f in update_plan['add_files'] + update_plan['update_files']):
            update_plan['update_type'] = 'hard_restart'
            update_plan['requires_restart'] = True
        elif any(f['path'] in ['main_simple.py', 'overlay_windows.py'] for f in update_plan['update_files']):
            update_plan['update_type'] = 'soft_restart'
            update_plan['requires_restart'] = True
        
        return update_plan
    
    def download_file_smart(self, file_info, destination):
        """Smart file download with multiple fallback methods"""
        url = file_info['url']
        expected_hash = file_info.get('hash', '')
        expected_size = file_info.get('size', 0)
        
        # Try cache first
        cache_path = os.path.join(self.update_cache, expected_hash[:16])
        if os.path.exists(cache_path) and self._calculate_file_hash(cache_path) == expected_hash:
            shutil.copy2(cache_path, destination)
            return True
        
        # Download methods in order of preference
        download_methods = [
            self._download_direct,
            self._download_via_cdn,
            self._download_via_github_api,
            self._download_chunked
        ]
        
        for method in download_methods:
            try:
                if method(url, destination):
                    # Verify download
                    if expected_hash and self._calculate_file_hash(destination) != expected_hash:
                        os.remove(destination)
                        continue
                    
                    # Cache successful download
                    shutil.copy2(destination, cache_path)
                    return True
            except:
                continue
        
        return False
    
    def _download_direct(self, url, destination):
        """Direct download"""
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(destination, 'wb') as f:
                f.write(response.content)
            return True
        return False
    
    def _download_via_cdn(self, url, destination):
        """Download via CDN (jsDelivr)"""
        # Convert GitHub URL to jsDelivr CDN
        if 'github.com' in url or 'githubusercontent.com' in url:
            cdn_url = f"https://cdn.jsdelivr.net/gh/{self.github_user}/{self.github_repo}@{self.branch}/"
            file_path = url.split(self.branch + '/')[-1]
            cdn_url += file_path
            
            response = requests.get(cdn_url, timeout=30)
            if response.status_code == 200:
                with open(destination, 'wb') as f:
                    f.write(response.content)
                return True
        return False
    
    def _download_via_github_api(self, url, destination):
        """Download via GitHub API with authentication if available"""
        # Convert raw URL to API URL
        if 'raw.githubusercontent.com' in url:
            path = url.split(self.branch + '/')[-1]
            api_url = f"{self.api_base}/contents/{path}"
            
            response = requests.get(api_url, timeout=30)
            if response.status_code == 200:
                import base64
                content = response.json().get('content', '')
                decoded = base64.b64decode(content)
                with open(destination, 'wb') as f:
                    f.write(decoded)
                return True
        return False
    
    def _download_chunked(self, url, destination):
        """Download in chunks with resume support"""
        headers = {}
        mode = 'wb'
        
        if os.path.exists(destination + '.part'):
            headers['Range'] = f'bytes={os.path.getsize(destination + ".part")}-'
            mode = 'ab'
        
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        with open(destination + '.part', mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        os.rename(destination + '.part', destination)
        return True
    
    def create_backup(self):
        """Create complete backup of current installation"""
        backup_name = f"backup_{self.current_version}_{int(time.time())}"
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        # Create zip backup for space efficiency
        zip_path = backup_path + '.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in self.current_files:
                full_path = os.path.join(self.app_dir, file_path)
                if os.path.exists(full_path):
                    zipf.write(full_path, file_path)
        
        # Keep only last 3 backups to save space
        self._cleanup_old_backups()
        
        return zip_path
    
    def _cleanup_old_backups(self):
        """Keep only the most recent backups"""
        backups = sorted([f for f in os.listdir(self.backup_dir) if f.endswith('.zip')])
        if len(backups) > 3:
            for old_backup in backups[:-3]:
                os.remove(os.path.join(self.backup_dir, old_backup))
    
    def apply_update_plan(self, update_plan):
        """Apply the update plan with intelligent handling"""
        success_count = 0
        fail_count = 0
        
        # Phase 1: Delete obsolete files
        for file_path in update_plan['delete_files']:
            try:
                full_path = os.path.join(self.app_dir, file_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
                    print(f"[UltimateUpdater] Deleted: {file_path}")
                success_count += 1
            except Exception as e:
                print(f"[UltimateUpdater] Failed to delete {file_path}: {e}")
                fail_count += 1
        
        # Phase 2: Create new directories
        for file_info in update_plan['add_files']:
            dir_path = os.path.dirname(os.path.join(self.app_dir, file_info['path']))
            os.makedirs(dir_path, exist_ok=True)
        
        # Phase 3: Download and apply new/updated files
        for file_info in update_plan['add_files'] + update_plan['update_files']:
            try:
                temp_path = os.path.join(self.temp_dir, file_info['path'])
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                
                # Download file
                if self.download_file_smart(file_info, temp_path):
                    # Move to final location
                    final_path = os.path.join(self.app_dir, file_info['path'])
                    
                    # Handle locked files (especially on Windows)
                    if os.path.exists(final_path):
                        try:
                            os.remove(final_path)
                        except:
                            # File is locked, schedule for update on restart
                            self._schedule_file_replacement(temp_path, final_path)
                            continue
                    
                    shutil.move(temp_path, final_path)
                    print(f"[UltimateUpdater] Updated: {file_info['path']}")
                    
                    # Try hot reload if it's a Python module
                    if file_info['path'].endswith('.py'):
                        self._try_hot_reload(file_info['path'])
                    
                    success_count += 1
                else:
                    fail_count += 1
                    
            except Exception as e:
                print(f"[UltimateUpdater] Failed to update {file_info['path']}: {e}")
                fail_count += 1
        
        # Clean up temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        return success_count, fail_count
    
    def _try_hot_reload(self, file_path):
        """Attempt to hot-reload a Python module"""
        try:
            # Convert file path to module name
            module_name = file_path.replace('.py', '').replace(os.sep, '.')
            
            if module_name in sys.modules:
                # Module is loaded, try to reload it
                importlib.reload(sys.modules[module_name])
                print(f"[UltimateUpdater] Hot-reloaded: {module_name}")
                
                # Re-initialize if it's a critical module
                if self.app and module_name == 'simple_gemini_provider':
                    # Reinitialize Gemini provider
                    if hasattr(self.app, 'initialize_gemini'):
                        self.app.initialize_gemini(self.app.current_api_key)
                
                return True
            return False
            
        except Exception as e:
            print(f"[UltimateUpdater] Hot-reload failed for {file_path}: {e}")
            return False
    
    def _schedule_file_replacement(self, source, destination):
        """Schedule file replacement for next restart (Windows)"""
        if sys.platform == 'win32':
            # Create a batch script that will run on next startup
            batch_content = f'''@echo off
timeout /t 2 /nobreak > nul
move /y "{source}" "{destination}"
del "%~f0"
'''
            batch_path = os.path.join(self.app_dir, f"pending_update_{int(time.time())}.bat")
            with open(batch_path, 'w') as f:
                f.write(batch_content)
            
            # Add to Windows startup (Run Once)
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Microsoft\Windows\CurrentVersion\RunOnce", 
                                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, f"GoStealthAI_Update_{int(time.time())}", 0, 
                            winreg.REG_SZ, batch_path)
            winreg.CloseKey(key)
    
    def perform_complete_update(self, manifest):
        """Perform a complete update based on manifest"""
        try:
            # Analyze what needs updating
            update_plan = self.analyze_update_requirements(manifest)
            
            # Check if update is needed
            total_changes = (len(update_plan['add_files']) + 
                           len(update_plan['update_files']) + 
                           len(update_plan['delete_files']))
            
            if total_changes == 0:
                print("[UltimateUpdater] No changes needed")
                return True, "Already up to date"
            
            print(f"[UltimateUpdater] Update plan: {total_changes} changes")
            print(f"  - Add: {len(update_plan['add_files'])} files")
            print(f"  - Update: {len(update_plan['update_files'])} files")
            print(f"  - Delete: {len(update_plan['delete_files'])} files")
            print(f"  - Download size: {update_plan['total_download_size'] / 1024 / 1024:.2f} MB")
            
            # Create backup
            backup_path = self.create_backup()
            print(f"[UltimateUpdater] Backup created: {backup_path}")
            
            # Apply updates
            success, failed = self.apply_update_plan(update_plan)
            
            if failed == 0:
                # Update version
                self.current_version = manifest['version']
                self._save_version_info(manifest)
                
                # Handle restart if needed
                if update_plan['requires_restart']:
                    return True, f"Update complete! Restart required ({update_plan['update_type']})"
                else:
                    return True, f"Update complete! {success} files updated (hot-reloaded)"
            else:
                # Partial success
                return False, f"Partial update: {success} succeeded, {failed} failed"
                
        except Exception as e:
            print(f"[UltimateUpdater] Update failed: {e}")
            return False, str(e)
    
    def _save_version_info(self, manifest):
        """Save version information locally"""
        version_file = os.path.join(self.app_dir, 'version_info.json')
        with open(version_file, 'w') as f:
            json.dump({
                'version': manifest['version'],
                'updated': datetime.now().isoformat(),
                'update_id': manifest.get('update_id', ''),
                'branch': self.branch
            }, f, indent=2)
    
    def check_and_update(self, auto_apply=False):
        """Main update check and apply method"""
        try:
            # Fetch manifest
            manifest = self.fetch_dynamic_manifest()
            if not manifest:
                return False, "Could not fetch update manifest"
            
            # Check version
            has_update, update_type = self.compare_versions(manifest)
            
            if not has_update:
                return False, "Already on latest version"
            
            print(f"[UltimateUpdater] Update available: {self.current_version} → {manifest['version']}")
            
            if auto_apply or manifest.get('force_update', False):
                # Apply update automatically
                return self.perform_complete_update(manifest)
            else:
                # Just notify about update
                return True, f"Update {manifest['version']} available"
                
        except Exception as e:
            print(f"[UltimateUpdater] Check failed: {e}")
            return False, str(e)
    
    def create_self_updating_exe(self):
        """Create a wrapper EXE that can update itself"""
        wrapper_code = '''
import os
import sys
import time
import subprocess
import shutil

def main():
    # Check for pending update
    if os.path.exists("GoStealthAI.exe.new"):
        print("Applying self-update...")
        time.sleep(2)
        
        # Replace current EXE
        if os.path.exists("GoStealthAI.exe.old"):
            os.remove("GoStealthAI.exe.old")
        os.rename("GoStealthAI.exe", "GoStealthAI.exe.old")
        os.rename("GoStealthAI.exe.new", "GoStealthAI.exe")
        
        # Restart with new version
        subprocess.Popen(["GoStealthAI.exe"] + sys.argv[1:])
        sys.exit(0)
    
    # Run the actual app
    import main_simple
    main_simple.main()

if __name__ == "__main__":
    main()
'''
        
        wrapper_path = os.path.join(self.app_dir, 'launcher_wrapper.py')
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_code)
        
        return wrapper_path


# Standalone functions for testing
def create_github_structure():
    """Create the required structure on GitHub"""
    structure = {
        "version": "1.0.2",
        "update_id": "update_2024_01_15",
        "release_date": "2024-01-15",
        "update_strategy": "progressive",
        "force_update": False,
        "minimum_version": "1.0.0",
        "changelog": "Dynamic update system implemented",
        "structure": {
            # This will be auto-generated from your GitHub repo
            # The updater will scan all files and create this structure
        }
    }
    
    print("Upload this structure as 'update_system/manifest.json' to your GitHub repo:")
    print(json.dumps(structure, indent=2))


def test_updater():
    """Test the updater system"""
    updater = UltimateUpdater(current_version="1.0.1")
    
    # Check for updates
    success, message = updater.check_and_update(auto_apply=False)
    print(f"Update check: {success} - {message}")
    
    if success:
        response = input("Apply update? (y/n): ")
        if response.lower() == 'y':
            success, message = updater.perform_complete_update(
                updater.fetch_dynamic_manifest()
            )
            print(f"Update result: {success} - {message}")


if __name__ == "__main__":
    test_updater()
