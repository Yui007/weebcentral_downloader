#!/usr/bin/env python3
"""
FlareSolverr Auto-Start Script
This script helps download and start FlareSolverr automatically.
"""

import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import json
from pathlib import Path

FLARESOLVERR_VERSION = "v3.3.21"
FLARESOLVERR_PORT = 8191

def check_flaresolverr_running():
    """Check if FlareSolverr is already running"""
    try:
        import requests
        response = requests.get(f"http://localhost:{FLARESOLVERR_PORT}/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def download_flaresolverr():
    """Download FlareSolverr for the current platform"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Determine the correct download URL
    if system == "windows":
        if "amd64" in machine or "x86_64" in machine:
            filename = "flaresolverr_windows_x64.exe"
        else:
            filename = "flaresolverr_windows_x86.exe"
    elif system == "linux":
        if "amd64" in machine or "x86_64" in machine:
            filename = "flaresolverr_linux_x64"
        elif "arm" in machine or "aarch64" in machine:
            filename = "flaresolverr_linux_arm64"
        else:
            print(f"❌ Unsupported Linux architecture: {machine}")
            return None
    elif system == "darwin":  # macOS
        if "arm64" in machine or "aarch64" in machine:
            filename = "flaresolverr_macos_arm64"
        else:
            filename = "flaresolverr_macos_x64"
    else:
        print(f"❌ Unsupported platform: {system}")
        return None
    
    download_url = f"https://github.com/FlareSolverr/FlareSolverr/releases/download/{FLARESOLVERR_VERSION}/{filename}"
    
    print(f"📥 Downloading FlareSolverr {FLARESOLVERR_VERSION}...")
    print(f"   URL: {download_url}")
    
    # Create a directory for FlareSolverr
    fs_dir = Path.home() / ".flaresolverr"
    fs_dir.mkdir(exist_ok=True)
    
    # Download the file
    try:
        file_path = fs_dir / filename
        
        # Show progress
        def reporthook(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(block_num * block_size * 100 / total_size, 100)
                print(f"\r   Progress: {percent:.1f}%", end='', flush=True)
        
        urllib.request.urlretrieve(download_url, file_path, reporthook)
        print()  # New line after progress
        
        # Verify download
        if not file_path.exists() or file_path.stat().st_size == 0:
            print(f"❌ Download failed: File is empty or missing")
            return None
        
        # Make executable on Unix-like systems
        if system != "windows":
            os.chmod(file_path, 0o755)
        
        print(f"✅ Downloaded to: {file_path}")
        return file_path
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.reason}")
        print(f"   URL: {download_url}")
        return None
    except Exception as e:
        print(f"❌ Failed to download: {e}")
        return None

def start_flaresolverr(executable_path):
    """Start FlareSolverr in the background"""
    print(f"🚀 Starting FlareSolverr...")
    
    try:
        # Verify executable exists and is executable
        if not executable_path.exists():
            print(f"❌ Executable not found: {executable_path}")
            return False
        
        if platform.system() == "Windows":
            # On Windows, start in a new window without blocking
            subprocess.Popen([str(executable_path)], 
                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                           shell=False,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        else:
            # On Unix-like systems, run in background
            subprocess.Popen([str(executable_path)], 
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           start_new_session=True)
        
        # Wait for it to start with progress indicator
        import time
        print("   Waiting for startup", end='', flush=True)
        for i in range(6):  # Wait up to 6 seconds
            time.sleep(1)
            print(".", end='', flush=True)
            if check_flaresolverr_running():
                print()
                print(f"✅ FlareSolverr is now running on port {FLARESOLVERR_PORT}")
                print(f"   Health check: http://localhost:{FLARESOLVERR_PORT}/health")
                return True
        
        print()
        print("❌ FlareSolverr failed to start within timeout")
        print("💡 Try starting it manually to see error messages:")
        print(f"   {executable_path}")
        return False
            
    except FileNotFoundError:
        print(f"❌ Executable not found: {executable_path}")
        return False
    except PermissionError:
        print(f"❌ Permission denied. Make sure the file is executable:")
        print(f"   chmod +x {executable_path}")
        return False
    except Exception as e:
        print(f"❌ Failed to start FlareSolverr: {e}")
        return False

def main():
    print("=" * 60)
    print("🔥 FlareSolverr Auto-Start Helper")
    print("=" * 60)
    
    # Check if already running
    if check_flaresolverr_running():
        print(f"✅ FlareSolverr is already running on port {FLARESOLVERR_PORT}")
        return
    
    # Look for existing FlareSolverr executable
    fs_dir = Path.home() / ".flaresolverr"
    executable_path = None
    
    if fs_dir.exists():
        # Look for executable files (not .zip, .txt, etc.)
        for file in fs_dir.iterdir():
            if file.is_file() and not file.suffix in ['.zip', '.txt', '.md', '.log']:
                if platform.system() != "Windows" or file.suffix == '.exe':
                    executable_path = file
                    print(f"📁 Found existing FlareSolverr: {file.name}")
                    break
    
    # If not found, download it
    if not executable_path or not executable_path.exists():
        executable_path = download_flaresolverr()
        if not executable_path:
            print("\n❌ Failed to set up FlareSolverr")
            print("\n📖 Manual setup instructions:")
            print("1. Visit: https://github.com/FlareSolverr/FlareSolverr/releases")
            print("2. Download the appropriate version for your system")
            print("3. Extract and run the executable")
            print("4. Ensure it's running on port 8191")
            sys.exit(1)
    
    # Start FlareSolverr
    if start_flaresolverr(executable_path):
        print("\n🎉 Setup complete! You can now use the downloader.")
        print("💡 FlareSolverr will automatically handle Cloudflare challenges.")
        print("   Leave it running in the background while downloading.")
    else:
        print("\n❌ Failed to start FlareSolverr automatically")
        print("📖 Try starting it manually:")
        print(f"   {executable_path}")

if __name__ == "__main__":
    main()
