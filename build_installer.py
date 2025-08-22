# build_installer.py
"""
Build script to create the installer executable
"""

import PyInstaller.__main__
import os
import shutil

def build_installer():
    """Build the installer executable"""
    
    # Clean previous builds
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
    
    # PyInstaller arguments
    args = [
        'smart_installer.py',
        '--onefile',
        '--windowed',  # No console window for installer
        '--name=GoStealthAI_Setup',
        '--icon=icon.ico',  # Add your icon
        '--add-data=main_simple.py;.',
        '--add-data=launcher.py;.',
        '--add-data=overlay_windows.py;.',
        '--add-data=advanced_capture.py;.',
        '--add-data=simple_gemini_provider.py;.',
        '--add-data=simple_ocr.py;.',
        '--add-data=ui_automation_capture.py;.',
        '--add-data=prompt.txt;.',
        '--add-data=settings.json;.',
        '--hidden-import=pynput',
        '--hidden-import=PyQt5',
        '--hidden-import=PIL',
        '--hidden-import=requests',
        '--uac-admin',  # Request admin on Windows 7/8
        '--version-file=version_info.txt'
    ]
    
    # Build
    PyInstaller.__main__.run(args)
    
    print("\n✅ Installer built successfully!")
    print(f"📦 Output: dist/GoStealthAI_Setup.exe")

if __name__ == "__main__":
    build_installer()