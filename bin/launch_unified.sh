#!/bin/bash

# Unified Music Library Launcher
# =============================
# Launches the unified web interface with automatic setup and environment management

echo "🎵 Unified Music Library Management System"
echo "=========================================="
echo

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to check if Python 3 is available
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        # Check if it's Python 3
        python --version 2>&1 | grep -q "Python 3"
        if [ $? -eq 0 ]; then
            PYTHON_CMD="python"
        else
            echo "❌ Python 3 is required but not found!"
            echo "Please install Python 3 and try again."
            exit 1
        fi
    else
        echo "❌ Python 3 is required but not found!"
        echo "Please install Python 3 and try again."
        exit 1
    fi
    echo "✅ Found Python: $($PYTHON_CMD --version)"
}

# Function to create virtual environment
create_venv() {
    # Use platform-specific environment name
    VENV_NAME="music_env_$(uname -s | tr '[:upper:]' '[:lower:]')"
    
    if [ ! -d "$VENV_NAME" ]; then
        echo "🔧 Creating virtual environment for $(uname -s)..."
        $PYTHON_CMD -m venv "$VENV_NAME"
        if [ $? -ne 0 ]; then
            echo "❌ Failed to create virtual environment!"
            echo "Please ensure you have the 'venv' module installed."
            exit 1
        fi
        echo "✅ Virtual environment created successfully: $VENV_NAME"
    else
        echo "✅ Virtual environment already exists: $VENV_NAME"
    fi
    
    # Set the environment name for other functions
    export VENV_NAME
}

# Function to activate virtual environment
activate_venv() {
    echo "🔧 Activating virtual environment..."
    source "$VENV_NAME/bin/activate"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to activate virtual environment!"
        exit 1
    fi
    echo "✅ Virtual environment activated: $VENV_NAME"
}

# Function to install requirements
install_requirements() {
    if [ -f "requirements.txt" ]; then
        echo "📦 Installing dependencies from requirements.txt..."
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install dependencies from requirements.txt!"
            echo "Trying to install core dependencies manually..."
            pip install flask flask-cors mutagen pillow
            if [ $? -ne 0 ]; then
                echo "❌ Failed to install dependencies!"
                exit 1
            fi
        fi
        echo "✅ Dependencies installed successfully!"
    else
        echo "⚠️  requirements.txt not found, installing core dependencies..."
        pip install flask flask-cors mutagen pillow
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install core dependencies!"
            exit 1
        fi
        echo "✅ Core dependencies installed successfully!"
    fi
}

# Function to check dependencies
check_dependencies() {
    echo "🔍 Checking dependencies..."
    python -c "import flask, flask_cors, mutagen, PIL" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ Missing dependencies detected!"
        echo "Installing required packages..."
        pip install flask flask-cors mutagen pillow
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install dependencies!"
            exit 1
        fi
    fi
    echo "✅ All dependencies are available!"
}

# Function to setup directories
setup_directories() {
    echo "📁 Setting up directories..."
    cd ..
    mkdir -p Library New Duplicate Trash
    cd "$SCRIPT_DIR"
    mkdir -p thumbnails  # Thumbnails directory in scripts folder
    echo "✅ Directories created successfully!"
}

# Main execution
echo "🔧 Setting up Python environment..."

# Check Python availability
check_python

# Create virtual environment
create_venv

# Activate virtual environment
activate_venv

# Install requirements
install_requirements

# Check dependencies
check_dependencies

# Setup directories
setup_directories

# Launch the unified web interface
echo
echo "🚀 Launching unified web interface..."
echo "📱 Opening browser in 3 seconds..."
echo "⏹️  Press Ctrl+C to stop"
echo

# Open browser after a short delay
(sleep 3 && open http://localhost:8088 2>/dev/null || xdg-open http://localhost:8088 2>/dev/null || echo "📱 Please open your browser to: http://localhost:8088") &

# Launch the Python script
python launch_unified.py
