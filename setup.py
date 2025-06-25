#!/usr/bin/env python3
"""
Setup script for Multilingual Customer Service Agent

This script helps set up the environment and install dependencies.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("=" * 60)
    print("MULTILINGUAL CUSTOMER SERVICE AGENT SETUP")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version.split()[0]} detected")
    
    # Create virtual environment if it doesn't exist
    if not os.path.exists("ai_env"):
        if not run_command("python3 -m venv ai_env", "Creating virtual environment"):
            sys.exit(1)
    else:
        print("✓ Virtual environment already exists")
    
    # Activate virtual environment and install dependencies
    if sys.platform == "win32":
        activate_cmd = "ai_env\\Scripts\\activate"
        pip_cmd = "ai_env\\Scripts\\pip"
    else:
        activate_cmd = "source ai_env/bin/activate"
        pip_cmd = "ai_env/bin/pip"
    
    # Upgrade pip
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        sys.exit(1)
    
    # Install requirements
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing dependencies"):
        print("\n⚠️  Some dependencies might have failed to install.")
        print("You may need to install them manually:")
        print("1. Activate the virtual environment:")
        if sys.platform == "win32":
            print("   ai_env\\Scripts\\activate")
        else:
            print("   source ai_env/bin/activate")
        print("2. Install dependencies:")
        print("   pip install -r requirements.txt")
    
    # Create necessary directories
    directories = ["call_recordings", "processed_audio", "models"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETED!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Activate the virtual environment:")
    if sys.platform == "win32":
        print("   ai_env\\Scripts\\activate")
    else:
        print("   source ai_env/bin/activate")
    print("\n2. Add your call recordings to the 'call_recordings' directory")
    print("   Supported formats: .wav, .mp3, .m4a, .flac, .ogg")
    print("\n3. Run the complete pipeline:")
    print("   python complete_pipeline.py --mode all")
    print("\nOr run individual steps:")
    print("   python complete_pipeline.py --mode process  # Process audio")
    print("   python complete_pipeline.py --mode train    # Train models")
    print("   python complete_pipeline.py --mode serve    # Deploy agent")

if __name__ == "__main__":
    main()
