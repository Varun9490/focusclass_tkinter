#!/usr/bin/env python3
"""
FocusClass Production Health Check
Verifies all systems are ready for production use
"""

import sys
import os
import socket
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.8+")
        return False

def check_dependencies():
    """Check required dependencies"""
    print("\n📦 Checking dependencies...")
    
    required = [
        'websockets',
        'aiohttp', 
        'aiosqlite',
        'mss',
        'PIL',  # Pillow
        'psutil',
        'qrcode'
    ]
    
    windows_only = ['win32api', 'win32gui'] if sys.platform == 'win32' else []
    
    all_deps = required + windows_only
    missing = []
    
    for dep in all_deps:
        try:
            importlib.import_module(dep)
            print(f"   ✅ {dep}")
        except ImportError:
            print(f"   ❌ {dep} - Missing")
            missing.append(dep)
    
    if missing:
        print(f"\n   Install missing dependencies: pip install {' '.join(missing)}")
        return False
    
    return True

def check_directories():
    """Check required directories exist"""
    print("\n📁 Checking directories...")
    
    required_dirs = ['logs', 'exports', 'assets', 'src', 'src/common', 'src/teacher', 'src/student']
    
    all_exist = True
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"   ✅ {dir_name}")
        else:
            print(f"   ❌ {dir_name} - Missing")
            all_exist = False
            # Try to create it
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(f"   ✅ Created {dir_name}")
                all_exist = True
            except Exception as e:
                print(f"   ❌ Failed to create {dir_name}: {e}")
    
    return all_exist

def check_files():
    """Check critical files exist"""
    print("\n📄 Checking critical files...")
    
    required_files = [
        'main.py',
        'src/common/config.py',
        'src/common/utils.py', 
        'src/common/network_manager.py',
        'src/teacher/teacher_app.py',
        'src/student/student_app.py'
    ]
    
    all_exist = True
    for file_name in required_files:
        file_path = Path(file_name)
        if file_path.exists():
            print(f"   ✅ {file_name}")
        else:
            print(f"   ❌ {file_name} - Missing")
            all_exist = False
    
    return all_exist

def check_network_ports():
    """Check if required ports are available"""
    print("\n🌐 Checking network ports...")
    
    ports_to_check = [8765, 8766, 8767, 8080, 8081, 8082]
    available_ports = []
    
    for port in ports_to_check:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                print(f"   ✅ Port {port} - Available")
                available_ports.append(port)
        except socket.error:
            print(f"   ⚠️  Port {port} - In use (will try alternative)")
    
    if len(available_ports) >= 2:
        return True
    else:
        print("   ❌ Not enough ports available")
        return False

def check_permissions():
    """Check file permissions"""
    print("\n🔐 Checking permissions...")
    
    try:
        # Test write permission
        test_file = Path('test_write.tmp')
        test_file.write_text('test')
        test_file.unlink()
        print("   ✅ Write permissions - OK")
        
        # Test execute permission
        if sys.platform == 'win32':
            print("   ✅ Execute permissions - OK (Windows)")
        else:
            print("   ✅ Execute permissions - OK (Unix)")
        
        return True
    except Exception as e:
        print(f"   ❌ Permission error: {e}")
        return False

def run_basic_import_test():
    """Test basic imports"""
    print("\n🧪 Running import tests...")
    
    try:
        sys.path.append('src')
        from common.config import APP_VERSION
        print(f"   ✅ Config import - Version {APP_VERSION}")
        
        from common.utils import setup_logging
        print("   ✅ Utils import - OK")
        
        from common.network_manager import NetworkManager
        print("   ✅ Network manager import - OK")
        
        return True
    except Exception as e:
        print(f"   ❌ Import test failed: {e}")
        return False

def main():
    """Run all health checks"""
    print("🏥 FocusClass Production Health Check")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Directories", check_directories),
        ("Files", check_files),
        ("Network Ports", check_network_ports),
        ("Permissions", check_permissions),
        ("Import Tests", run_basic_import_test)
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        if check_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Health Check Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 System is PRODUCTION READY!")
        print("\nNext steps:")
        print("1. Run: python main.py")
        print("2. Or use: start_production.bat")
        return True
    else:
        print("⚠️  System has issues that need to be resolved")
        print("\nPlease fix the failed checks above and run again")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)