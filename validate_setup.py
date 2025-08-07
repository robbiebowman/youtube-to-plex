#!/usr/bin/env python3
"""
Validation script for YouTube to Plex Downloader Phase 1 & 2 implementation.
This script validates:
1. Project structure
2. Dependencies installation
3. Configuration loading and validation
4. Logging framework setup
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path


def check_project_structure():
    """Check if all required directories and files exist."""
    print("🔍 Checking project structure...")
    
    required_dirs = ['src', 'logs', 'tests']
    required_files = [
        'requirements.txt',
        'config.yaml',
        '.env.example',
        'src/__init__.py',
        'src/config.py',
        'src/logging_config.py',
        'tech-design.md'
    ]
    
    missing_items = []
    
    # Check directories
    for dir_name in required_dirs:
        if not os.path.isdir(dir_name):
            missing_items.append(f"Directory: {dir_name}")
    
    # Check files
    for file_name in required_files:
        if not os.path.isfile(file_name):
            missing_items.append(f"File: {file_name}")
    
    if missing_items:
        print("❌ Missing project structure items:")
        for item in missing_items:
            print(f"   - {item}")
        return False
    else:
        print("✅ Project structure is complete")
        return True


def check_virtual_environment():
    """Check if running in a virtual environment."""
    print("🔍 Checking virtual environment...")
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
        return True
    else:
        print("⚠️  Not running in a virtual environment")
        print("   Recommendation: Create and activate a virtual environment:")
        print("   python -m venv venv")
        print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        return False


def check_dependencies():
    """Check if all required dependencies can be imported."""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        ('yaml', 'PyYAML'),
        ('pydantic', 'pydantic'),
        ('dotenv', 'python-dotenv'),
        ('fuzzywuzzy', 'fuzzywuzzy'),
        ('Levenshtein', 'python-levenshtein'),
        ('googleapiclient', 'google-api-python-client'),
        ('schedule', 'schedule'),
        ('feedparser', 'feedparser')
    ]
    
    missing_packages = []
    
    for import_name, package_name in required_packages:
        try:
            importlib.import_module(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name}")
    
    if missing_packages:
        print("\n📦 To install missing packages:")
        print("pip install -r requirements.txt")
        return False
    else:
        print("✅ All dependencies are installed")
        return True


def check_config_loading():
    """Test configuration loading and validation."""
    print("🔍 Testing configuration loading...")
    
    try:
        # Add src to Python path
        sys.path.insert(0, 'src')
        from config import load_config, validate_config_file
        
        # Test basic config loading (will fail on missing env vars but that's expected)
        try:
            config = load_config()
            print("✅ Configuration file loads successfully")
            
            # Check basic structure
            assert hasattr(config, 'youtube'), "Missing youtube section"
            assert hasattr(config, 'filters'), "Missing filters section"
            assert hasattr(config, 'download'), "Missing download section"
            assert hasattr(config, 'storage'), "Missing storage section"
            assert hasattr(config, 'schedule'), "Missing schedule section"
# Notifications section removed - using logs only
            assert hasattr(config, 'logging'), "Missing logging section"
            
            print("✅ Configuration structure is valid")
            
        except ValueError as e:
            if "YOUTUBE_API_KEY" in str(e):
                print("⚠️  Configuration loads but missing API key (expected)")
                print("   Create .env file with YOUTUBE_API_KEY")
            else:
                print(f"❌ Configuration validation error: {e}")
                return False
        
        # Test validation function
        result = validate_config_file()
        if result:
            print("✅ Configuration validation passes")
        else:
            print("⚠️  Configuration validation warns about missing environment variables")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False


def check_logging_setup():
    """Test logging framework setup."""
    print("🔍 Testing logging framework...")
    
    try:
        sys.path.insert(0, 'src')
        from config import LoggingConfig
        from logging_config import setup_logging, get_logger, LoggerMixin
        
        # Create test logging config
        log_config = LoggingConfig()
        
        # Test logger setup
        logger = setup_logging(log_config)
        print("✅ Logger setup successful")
        
        # Test logging functionality
        logger.info("Test log message from validation script")
        
        # Check if log file was created
        if os.path.exists(log_config.file_path):
            print("✅ Log file created successfully")
        else:
            print("❌ Log file not created")
            return False
        
        # Test child logger
        child_logger = get_logger('test_module')
        child_logger.debug("Test debug message")
        
        # Test mixin
        class TestClass(LoggerMixin):
            def test_method(self):
                self.logger.info("Test method called")
        
        test_obj = TestClass()
        test_obj.test_method()
        
        print("✅ Logging framework works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Logging setup failed: {e}")
        return False


def check_env_file():
    """Check for environment file setup."""
    print("🔍 Checking environment configuration...")
    
    if os.path.exists('.env'):
        print("✅ .env file exists")
        
        # Check if it has the required variables
        with open('.env', 'r') as f:
            content = f.read()
        
        required_vars = ['YOUTUBE_API_KEY']
        missing_vars = []
        
        for var in required_vars:
            if var not in content or f"{var}=" not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing variables in .env: {', '.join(missing_vars)}")
        else:
            print("✅ .env file has required variables")
        
        return len(missing_vars) == 0
    else:
        print("⚠️  .env file not found")
        print("   Copy .env.example to .env and add your API key")
        return False


def run_validation():
    """Run all validation checks."""
    print("🚀 YouTube to Plex Downloader - Phase 1 & 2 Validation")
    print("=" * 60)
    
    checks = [
        ("Project Structure", check_project_structure),
        ("Virtual Environment", check_virtual_environment),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Configuration Loading", check_config_loading),
        ("Logging Framework", check_logging_setup),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"\n{check_name}")
        print("-" * len(check_name))
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed with exception: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All validations passed! Phase 1 & 2 implementation is ready.")
        print("\nNext steps:")
        print("1. Get your YouTube API key and add it to .env")
        print("2. Update config.yaml with your target channel")
        print("3. Ready for Phase 3 implementation!")
    else:
        print("⚠️  Some validations failed. Please address the issues above.")
    
    return passed == total


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)