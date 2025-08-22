"""
GitHub Manifest Generator - Automatically creates update manifest from your repo
Run this locally or via GitHub Actions to generate manifest.json
"""
import os
import json
import hashlib
import requests
from datetime import datetime
from pathlib import Path


class ManifestGenerator:
    def __init__(self, github_user="Qsab1337", github_repo="Acebot", version="1.0.2"):
        self.github_user = github_user
        self.github_repo = github_repo
        self.version = version
        self.branch = "main"
        
        # Files/folders to exclude from manifest
        self.exclude_patterns = [
            '.git',
            '.github',
            '__pycache__',
            '.pyc',
            '.pyo',
            '.DS_Store',
            'Thumbs.db',
            '_backups',
            '_temp_update',
            '_update_cache',
            'test_',
            '.test',
            '.tmp',
            '.log'
        ]
        
        # Files that trigger different update types
        self.restart_triggers = {
            'hard': ['.exe', '.dll', '.so'],  # Requires full restart
            'soft': ['main_simple.py', 'overlay_windows.py', 'launcher.py'],  # Requires soft restart
            'none': ['.py', '.json', '.txt']  # Can be hot-reloaded
        }
    
    def should_exclude(self, path):
        """Check if file/folder should be excluded"""
        path_str = str(path).replace('\\', '/')
        for pattern in self.exclude_patterns:
            if pattern in path_str:
                return True
        return False
    
    def get_file_type(self, filename):
        """Determine file type for update strategy"""
        ext = os.path.splitext(filename)[1].lower()
        
        for update_type, extensions in self.restart_triggers.items():
            if ext in extensions or filename in extensions:
                return update_type
        
        return 'none'
    
    def calculate_file_hash(self, filepath):
        """Calculate SHA256 hash of a file"""
        sha256 = hashlib.sha256()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except:
            return None
    
    def scan_local_directory(self, directory):
        """Scan local directory and create manifest"""
        structure = {}
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(directory):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self.should_exclude(d)]
            
            for filename in files:
                if self.should_exclude(filename):
                    continue
                
                filepath = os.path.join(root, filename)
                relative_path = os.path.relpath(filepath, directory).replace('\\', '/')
                
                # Skip if it's our own generator
                if 'generate_manifest' in relative_path:
                    continue
                
                file_info = {
                    'path': relative_path,
                    'size': os.path.getsize(filepath),
                    'hash': self.calculate_file_hash(filepath),
                    'type': self.get_file_type(filename),
                    'url': f"https://raw.githubusercontent.com/{self.github_user}/{self.github_repo}/{self.branch}/{relative_path}"
                }
                
                structure[relative_path] = file_info
                total_size += file_info['size']
                file_count += 1
        
        return structure, total_size, file_count
    
    def scan_github_repo(self):
        """Scan GitHub repository via API and create manifest"""
        structure = {}
        
        def scan_tree(path=""):
            api_url = f"https://api.github.com/repos/{self.github_user}/{self.github_repo}/contents/{path}"
            
            try:
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    items = response.json()
                    
                    for item in items:
                        if self.should_exclude(item['name']):
                            continue
                        
                        if item['type'] == 'file':
                            file_info = {
                                'path': item['path'],
                                'size': item['size'],
                                'hash': item.get('sha', ''),
                                'type': self.get_file_type(item['name']),
                                'url': item['download_url']
                            }
                            structure[item['path']] = file_info
                            
                        elif item['type'] == 'dir':
                            # Recursively scan subdirectories
                            sub_structure = scan_tree(item['path'])
                            structure.update(sub_structure)
                
                return structure
            except Exception as e:
                print(f"Error scanning {path}: {e}")
                return {}
        
        return scan_tree()
    
    def generate_manifest(self, source='local', directory=None):
        """Generate complete manifest"""
        print(f"Generating manifest for version {self.version}...")
        
        if source == 'local' and directory:
            structure, total_size, file_count = self.scan_local_directory(directory)
        else:
            structure = self.scan_github_repo()
            total_size = sum(f['size'] for f in structure.values())
            file_count = len(structure)
        
        # Determine update requirements
        requires_restart = False
        update_type = 'hot_reload'
        
        for file_info in structure.values():
            if file_info['type'] == 'hard':
                requires_restart = True
                update_type = 'hard_restart'
                break
            elif file_info['type'] == 'soft' and update_type != 'hard_restart':
                requires_restart = True
                update_type = 'soft_restart'
        
        # Create manifest
        manifest = {
            'version': self.version,
            'update_id': f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'release_date': datetime.now().isoformat(),
            'branch': self.branch,
            'update_strategy': 'progressive',
            'force_update': False,
            'minimum_version': '1.0.0',
            'changelog': self._generate_changelog(),
            'statistics': {
                'total_files': file_count,
                'total_size': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2)
            },
            'update_requirements': {
                'requires_restart': requires_restart,
                'update_type': update_type,
                'estimated_time': self._estimate_update_time(total_size)
            },
            'structure': structure,
            'metadata': {
                'generator': 'ManifestGenerator v1.0',
                'generated': datetime.now().isoformat(),
                'github_user': self.github_user,
                'github_repo': self.github_repo
            }
        }
        
        return manifest
    
    def _generate_changelog(self):
        """Generate or fetch changelog"""
        # You can customize this to fetch from CHANGELOG.md or git commits
        changelog = """
- Enhanced auto-update system
- Added dynamic file discovery
- Improved hot-reload capability
- Fixed multiple capture methods
- Optimized for any future changes
        """.strip()
        
        return changelog
    
    def _estimate_update_time(self, total_size):
        """Estimate update time based on size"""
        # Assume 1MB/s download speed
        download_time = total_size / (1024 * 1024)
        
        if download_time < 5:
            return "Less than 5 seconds"
        elif download_time < 30:
            return "Less than 30 seconds"
        elif download_time < 60:
            return "About 1 minute"
        else:
            return f"About {int(download_time / 60)} minutes"
    
    def save_manifest(self, manifest, output_dir='.'):
        """Save manifest to file"""
        # Create update_system directory
        update_dir = os.path.join(output_dir, 'update_system')
        os.makedirs(update_dir, exist_ok=True)
        
        # Save manifest
        manifest_path = os.path.join(update_dir, 'manifest.json')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Manifest saved to: {manifest_path}")
        print(f"📊 Statistics:")
        print(f"  - Version: {manifest['version']}")
        print(f"  - Files: {manifest['statistics']['total_files']}")
        print(f"  - Size: {manifest['statistics']['total_size_mb']} MB")
        print(f"  - Update type: {manifest['update_requirements']['update_type']}")
        
        return manifest_path
    
    def create_github_action(self):
        """Create GitHub Action to auto-generate manifest on push"""
        action_yaml = """name: Generate Update Manifest

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  generate-manifest:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install requests
    
    - name: Generate manifest
      run: |
        python generate_manifest.py --version ${{ github.event.head_commit.message || '1.0.2' }}
    
    - name: Commit manifest
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add update_system/manifest.json
        git commit -m "Auto-update manifest" || echo "No changes"
        git push
"""
        
        # Create .github/workflows directory
        workflow_dir = os.path.join('.github', 'workflows')
        os.makedirs(workflow_dir, exist_ok=True)
        
        # Save workflow
        workflow_path = os.path.join(workflow_dir, 'update-manifest.yml')
        with open(workflow_path, 'w') as f:
            f.write(action_yaml)
        
        print(f"✅ GitHub Action created: {workflow_path}")
        return workflow_path


def main():
    """Main entry point for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate update manifest for GoStealthAI')
    parser.add_argument('--version', default='1.0.2', help='Version number')
    parser.add_argument('--source', choices=['local', 'github'], default='local', 
                       help='Source to scan (local directory or GitHub repo)')
    parser.add_argument('--directory', default='.', help='Directory to scan (for local source)')
    parser.add_argument('--github-user', default='Qsab1337', help='GitHub username')
    parser.add_argument('--github-repo', default='Acebot', help='GitHub repository')
    parser.add_argument('--create-action', action='store_true', 
                       help='Create GitHub Action for auto-generation')
    
    args = parser.parse_args()
    
    # Create generator
    generator = ManifestGenerator(
        github_user=args.github_user,
        github_repo=args.github_repo,
        version=args.version
    )
    
    # Generate manifest
    if args.source == 'local':
        manifest = generator.generate_manifest(source='local', directory=args.directory)
    else:
        manifest = generator.generate_manifest(source='github')
    
    # Save manifest
    generator.save_manifest(manifest)
    
    # Create GitHub Action if requested
    if args.create_action:
        generator.create_github_action()
    
    print("\n📋 Next steps:")
    print("1. Review the generated manifest.json")
    print("2. Commit and push to your GitHub repo")
    print("3. The updater will automatically detect and apply updates")


if __name__ == "__main__":
    main()
