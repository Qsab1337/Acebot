# smart_installer.py - Fixed version without Unicode issues
"""
GoStealthAI Smart Installer - Unicode Safe Version
"""

import os
import sys
import shutil
import subprocess
import ctypes
import json
import time
import tempfile
import base64
from pathlib import Path
import traceback
import codecs

class GoStealthAIInstaller:
    def __init__(self):
        self.app_name = "GoStealthAI"
        self.app_version = "1.0.1"
        self.exe_name = "GoStealthAI.exe"
        
        # Installation paths
        self.install_dir = os.path.join(os.environ['LOCALAPPDATA'], 'GoStealthAI')
        self.desktop = Path.home() / 'Desktop'
        self.start_menu = Path(os.environ['APPDATA']) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
        self.app_data_dir = Path.home() / f'.{self.app_name}'
        
        # Get source directory
        if getattr(sys, 'frozen', False):
            self.source_dir = sys._MEIPASS
        else:
            self.source_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.installation_log = []
        self.defender_handled = False
    
    def log(self, message, level="INFO"):
        """Log installation steps"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.installation_log.append(log_entry)
        print(log_entry)
    
    def run_hidden_powershell(self, command, use_base64=True):
        """Run PowerShell command completely hidden"""
        try:
            if use_base64:
                # Encode command to bypass execution policy
                encoded = base64.b64encode(command.encode('utf-16le')).decode('ascii')
                ps_command = f'powershell -NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {encoded}'
            else:
                ps_command = f'powershell -NoProfile -NonInteractive -WindowStyle Hidden -Command "{command}"'
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                ps_command,
                shell=True,
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                timeout=5
            )
            
            return result.returncode == 0, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Timeout"
        except Exception as e:
            return False, "", str(e)
    
    def add_defender_exclusions(self):
        """Add Windows Defender exclusions using multiple methods"""
        self.log("Configuring Windows Defender exclusions...")
        
        paths = [self.install_dir, os.path.join(self.install_dir, self.exe_name)]
        
        # Method 1: Direct PowerShell
        ps_cmd = f"""
        $ErrorActionPreference = 'SilentlyContinue'
        Add-MpPreference -ExclusionPath '{self.install_dir}' -Force
        Add-MpPreference -ExclusionProcess '{self.exe_name}' -Force
        """
        
        success, _, _ = self.run_hidden_powershell(ps_cmd)
        if success:
            self.defender_handled = True
            self.log("Defender exclusions added successfully")
            return True
        
        # Method 2: Scheduled task
        try:
            task_name = f"GSA_Setup_{int(time.time())}"
            
            # Create PowerShell script
            ps_script_content = f"""
            Add-MpPreference -ExclusionPath '{self.install_dir}' -Force -ErrorAction SilentlyContinue
            Add-MpPreference -ExclusionProcess '{self.exe_name}' -Force -ErrorAction SilentlyContinue
            """
            
            # Save script to temp file with proper encoding
            script_path = os.path.join(tempfile.gettempdir(), f'{task_name}.ps1')
            with codecs.open(script_path, 'w', encoding='utf-8-sig') as f:
                f.write(ps_script_content)
            
            # Create and run scheduled task
            create_cmd = f'schtasks /create /tn "{task_name}" /tr "powershell -ExecutionPolicy Bypass -File \\"{script_path}\\"" /sc once /st 00:00 /ru SYSTEM /f'
            run_cmd = f'schtasks /run /tn "{task_name}"'
            delete_cmd = f'schtasks /delete /tn "{task_name}" /f'
            
            subprocess.run(create_cmd, shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(run_cmd, shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(1)
            subprocess.run(delete_cmd, shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Cleanup
            try:
                os.remove(script_path)
            except:
                pass
            
            self.defender_handled = True
            self.log("Defender exclusions added via scheduled task")
            return True
            
        except Exception as e:
            self.log(f"Scheduled task method failed: {str(e)}", "WARNING")
        
        # Method 3: WMI via PowerShell
        wmi_script = f"""
        $ErrorActionPreference = 'SilentlyContinue'
        try {{
            $defender = Get-WmiObject -Namespace root\\Microsoft\\Windows\\Defender -Class MSFT_MpPreference
            if ($defender) {{
                $defender.ExclusionPath += '{self.install_dir}'
                $defender.ExclusionProcess += '{self.exe_name}'
                $defender.Put() | Out-Null
            }}
        }} catch {{}}
        """
        
        success, _, _ = self.run_hidden_powershell(wmi_script)
        if success:
            self.defender_handled = True
            self.log("Defender exclusions added via WMI")
            return True
        
        self.log("Could not add Defender exclusions automatically", "WARNING")
        return False
    
    def copy_application_files(self):
        """Copy all embedded files to installation directory"""
        self.log("Installing application files...")
        
        # Create launcher.py with ASCII-safe content
        launcher_content = '''#!/usr/bin/env python3
"""
GoStealthAI Launcher
"""
import os
import sys
import time
import threading
from pathlib import Path

def show_splash():
    """Show startup splash screen"""
    print("=" * 50)
    print("     GoStealthAI v1.0.1 Starting")
    print("     Gemini 2.5 Pro (8192 tokens)")
    print("=" * 50)
    print("")
    print("Initializing...")
    time.sleep(1.5)
    
    # Hide console window
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.WinDLL('kernel32')
            user32 = ctypes.WinDLL('user32')
            hWnd = kernel32.GetConsoleWindow()
            if hWnd:
                user32.ShowWindow(hWnd, 0)
        except:
            pass

def main():
    """Main entry point"""
    try:
        show_splash()
        
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import and run main application
        from main_simple import main as main_app
        main_app()
        
    except ImportError as e:
        print(f"Error: Could not import main application: {e}")
        print("Please ensure all files are properly installed.")
        input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        # Write launcher with proper encoding
        launcher_path = os.path.join(self.install_dir, 'launcher.py')
        with codecs.open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_content)
        self.log("Created launcher.py")
        
        # Copy all Python files from embedded resources
        files_to_copy = [
            'main_simple.py',
            'overlay_windows.py',
            'advanced_capture.py',
            'simple_gemini_provider.py',
            'simple_ocr.py',
            'ui_automation_capture.py',
            'prompt.txt',
            'settings.json',
            'version.txt'
        ]
        
        copied_count = 0
        for filename in files_to_copy:
            source = os.path.join(self.source_dir, filename)
            dest = os.path.join(self.install_dir, filename)
            
            try:
                if os.path.exists(source):
                    # Copy file
                    shutil.copy2(source, dest)
                    copied_count += 1
                    self.log(f"  Installed {filename}")
                else:
                    # Create empty file if not found (for optional files)
                    if filename in ['api.txt', 'version.txt']:
                        with open(dest, 'w') as f:
                            if filename == 'version.txt':
                                f.write('1.0.1')
                            else:
                                f.write('')
                        self.log(f"  Created {filename}")
            except Exception as e:
                self.log(f"  Warning: Could not copy {filename}: {str(e)}", "WARNING")
        
        self.log(f"Installed {copied_count} files successfully")
        
        # Create the batch launcher
        self.create_batch_launcher()
    
    def create_batch_launcher(self):
        """Create a batch file launcher"""
        self.log("Creating batch launcher...")
        
        batch_content = f'''@echo off
cd /d "{self.install_dir}"
if exist "launcher.py" (
    python launcher.py
) else (
    echo Error: Application files not found
    echo Please reinstall GoStealthAI
    pause
)
'''
        
        batch_path = os.path.join(self.install_dir, 'GoStealthAI.bat')
        with open(batch_path, 'w') as f:
            f.write(batch_content)
        
        self.exe_name = "GoStealthAI.bat"
        self.log("Created batch launcher")
    
    def create_shortcuts(self):
        """Create desktop and start menu shortcuts"""
        self.log("Creating shortcuts...")
        
        target = os.path.join(self.install_dir, self.exe_name)
        
        # Desktop shortcut
        desktop_lnk = self.desktop / f"{self.app_name}.lnk"
        
        # PowerShell script to create shortcut
        ps_script = f'''
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{str(desktop_lnk)}")
        $Shortcut.TargetPath = "{target}"
        $Shortcut.WorkingDirectory = "{self.install_dir}"
        $Shortcut.Description = "GoStealthAI - AI-Powered Nursing Exam Assistant"
        $Shortcut.Save()
        '''
        
        success, _, _ = self.run_hidden_powershell(ps_script, use_base64=False)
        
        if success and desktop_lnk.exists():
            self.log("Desktop shortcut created")
            return True
        
        # Fallback: VBScript method
        try:
            vbs_content = f'''
Set WshShell = CreateObject("WScript.Shell")
Set oShellLink = WshShell.CreateShortcut("{str(desktop_lnk)}")
oShellLink.TargetPath = "{target}"
oShellLink.WorkingDirectory = "{self.install_dir}"
oShellLink.Description = "GoStealthAI"
oShellLink.Save
'''
            vbs_path = os.path.join(tempfile.gettempdir(), 'create_shortcut.vbs')
            with open(vbs_path, 'w') as f:
                f.write(vbs_content)
            
            subprocess.run(f'cscript //nologo "{vbs_path}"', shell=True, capture_output=True)
            os.remove(vbs_path)
            
            if desktop_lnk.exists():
                self.log("Desktop shortcut created (VBScript method)")
                return True
                
        except Exception as e:
            self.log(f"Could not create shortcut: {str(e)}", "WARNING")
        
        return False
    
    def add_firewall_rule(self):
        """Add Windows Firewall rule"""
        try:
            app_path = os.path.join(self.install_dir, 'launcher.py')
            rule_name = f"{self.app_name}_Allow"
            
            # Remove existing rule
            subprocess.run(
                f'netsh advfirewall firewall delete rule name="{rule_name}"',
                shell=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Add new rule
            cmd = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=allow program="python.exe" enable=yes'
            
            subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            self.log("Firewall rule added")
            return True
            
        except Exception as e:
            self.log(f"Could not add firewall rule: {str(e)}", "WARNING")
            return False
    
    def save_installation_info(self):
        """Save installation information"""
        try:
            info = {
                'version': self.app_version,
                'install_dir': self.install_dir,
                'install_date': time.time(),
                'defender_handled': self.defender_handled,
                'exe_name': self.exe_name
            }
            
            info_file = self.app_data_dir / 'installation.json'
            with codecs.open(str(info_file), 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=True)
            
            self.log("Installation info saved")
            return True
            
        except Exception as e:
            self.log(f"Could not save installation info: {str(e)}", "WARNING")
            return False
    
    def install(self):
        """Main installation process"""
        print("\n" + "=" * 50)
        print(f"   {self.app_name} v{self.app_version} Installer")
        print("=" * 50 + "\n")
        
        try:
            # Step 1: Create directories
            self.log(f"Creating installation directory...")
            os.makedirs(self.install_dir, exist_ok=True)
            self.app_data_dir.mkdir(exist_ok=True)
            
            # Step 2: Copy application files
            self.copy_application_files()
            
            # Step 3: Add Defender exclusions
            self.add_defender_exclusions()
            
            # Step 4: Add firewall rule
            self.add_firewall_rule()
            
            # Step 5: Create shortcuts
            self.create_shortcuts()
            
            # Step 6: Save installation info
            self.save_installation_info()
            
            # Show completion message
            print("\n" + "=" * 50)
            print("  INSTALLATION COMPLETE!")
            print("=" * 50)
            print("")
            print(f"  Installed to: {self.install_dir}")
            print("  Desktop shortcut created: Yes")
            
            if self.defender_handled:
                print("  Windows Defender configured: Yes")
            else:
                print("  Windows Defender: Manual config may be needed")
            
            print("")
            print("  You can now:")
            print("  1. Use the desktop shortcut to launch GoStealthAI")
            print("  2. Delete this installer")
            print("")
            print("=" * 50)
            print("\nPress Enter to exit...")
            input()
            
            return True
            
        except Exception as e:
            print(f"\nERROR: Installation failed: {str(e)}")
            print("\nDebug information:")
            print(traceback.format_exc())
            print("\nPress Enter to exit...")
            input()
            return False

def main():
    """Main entry point"""
    try:
        installer = GoStealthAIInstaller()
        installer.install()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print(traceback.format_exc())
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()