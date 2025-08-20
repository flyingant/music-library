#!/usr/bin/env python3
"""
Unified Music Library Launcher
==============================
Launches the unified web interface with automatic setup and dependency checking.
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def get_venv_path():
    """Get the path to the virtual environment"""
    script_dir = Path(__file__).parent
    
    # Use platform-specific environment name
    if os.name == 'nt':  # Windows
        venv_name = "music_env_windows"
    else:  # Unix/Linux/macOS
        import platform
        system = platform.system().lower()
        venv_name = f"music_env_{system}"
    
    return script_dir / venv_name

def is_venv_active():
    """Check if we're running in a virtual environment"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def create_venv():
    """Create a new virtual environment"""
    venv_path = get_venv_path()
    if venv_path.exists():
        print(f"✅ Virtual environment already exists at: {venv_path}")
        return True
    
    print("🔧 Creating virtual environment...")
    try:
        subprocess.check_call([sys.executable, '-m', 'venv', str(venv_path)])
        print(f"✅ Virtual environment created at: {venv_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating virtual environment: {e}")
        return False

def get_venv_python():
    """Get the path to the virtual environment's Python executable"""
    venv_path = get_venv_path()
    if os.name == 'nt':  # Windows
        return venv_path / "Scripts" / "python.exe"
    else:  # Unix/Linux/macOS
        return venv_path / "bin" / "python"

def get_venv_pip():
    """Get the path to the virtual environment's pip executable"""
    venv_path = get_venv_path()
    if os.name == 'nt':  # Windows
        return venv_path / "Scripts" / "pip.exe"
    else:  # Unix/Linux/macOS
        return venv_path / "bin" / "pip"

def install_requirements():
    """Install dependencies from requirements.txt"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        return False
    
    print("📦 Installing dependencies from requirements.txt...")
    try:
        pip_path = get_venv_pip()
        subprocess.check_call([str(pip_path), 'install', '-r', str(requirements_file)])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['flask', 'flask_cors', 'mutagen', 'PIL']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies():
    """Install missing dependencies"""
    print("🔧 Installing missing dependencies...")
    try:
        pip_path = get_venv_pip()
        subprocess.check_call([str(pip_path), 'install'] + missing_packages)
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def setup_directories():
    """Create necessary directories"""
    directories = [
        '../Library',
        '../New', 
        '../Duplicate',
        '../Trash',
        'thumbnails'  # Thumbnails now stored in current directory
    ]
    
    print("📁 Setting up directories...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")

def activate_venv():
    """Activate the virtual environment and restart the script if needed"""
    if is_venv_active():
        print("✅ Virtual environment is already active")
        return True
    
    venv_path = get_venv_path()
    if not venv_path.exists():
        print("❌ Virtual environment not found!")
        return False
    
    print("🔄 Activating virtual environment...")
    python_path = get_venv_python()
    
    # If we're not in the venv, restart with the venv's Python
    if str(python_path) != sys.executable:
        print(f"🔄 Restarting with virtual environment Python: {python_path}")
        os.execv(str(python_path), [str(python_path)] + sys.argv)
    
    return True

def main():
    print("🎵 Unified Music Library Management System")
    print("==========================================")
    print()
    
    # Setup virtual environment
    print("🔧 Setting up virtual environment...")
    if not create_venv():
        print("❌ Failed to create virtual environment")
        return
    
    # Activate virtual environment
    if not activate_venv():
        print("❌ Failed to activate virtual environment")
        return
    
    # Install requirements
    if not install_requirements():
        print("❌ Failed to install requirements")
        return
    
    # Check dependencies
    print("🔍 Checking dependencies...")
    missing_packages = check_dependencies()
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        response = input("Would you like to install them? (y/n): ")
        if response.lower() == 'y':
            if not install_dependencies():
                print("❌ Failed to install dependencies. Please install them manually:")
                print(f"pip install {' '.join(missing_packages)}")
                return
        else:
            print("❌ Cannot continue without required dependencies.")
            return
    else:
        print("✅ All dependencies are installed!")
    
    # Setup directories
    setup_directories()
    
    # Launch web interface
    print()
    print("🚀 Launching web interface...")
    print("📱 Opening browser in 3 seconds...")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(3)
        webbrowser.open('http://localhost:8088')
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Launch the unified web interface
    try:
        from unified_web_interface import app
        app.run(debug=False, host='0.0.0.0', port=8088)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Error launching web interface: {e}")
        print("Please check that all dependencies are installed correctly.")

if __name__ == '__main__':
    main()
