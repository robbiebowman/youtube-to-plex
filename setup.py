#!/usr/bin/env python3
"""
Setup script for YouTube to Plex Downloader.
Creates virtual environment and installs dependencies.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a shell command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {command}")
        print(f"   Error: {e.stderr}")
        return False


def setup_project():
    """Set up the project environment."""
    print("🚀 Setting up YouTube to Plex Downloader")
    print("=" * 50)
    
    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Already in virtual environment")
        in_venv = True
    else:
        print("📦 Creating virtual environment...")
        in_venv = False
        
        # Create virtual environment
        if not run_command("python3 -m venv venv", "Create virtual environment"):
            return False
        
        print("⚠️  Virtual environment created.")
        print("   Please activate it and run this script again:")
        print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        print("   python setup.py")
        return False
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Install dependencies"):
        return False
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        print("📝 Creating .env file from template...")
        if os.path.exists('.env.example'):
            run_command("cp .env.example .env", "Copy .env template")
            print("⚠️  Please edit .env file and add your YouTube API key")
        else:
            print("❌ .env.example not found")
            return False
    else:
        print("✅ .env file already exists")
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    print("✅ Created logs directory")
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file and add your YouTube API key")
    print("2. Update config.yaml with your target channel")
    print("3. Run validation: python validate_setup.py")
    
    return True


if __name__ == "__main__":
    success = setup_project()
    sys.exit(0 if success else 1)