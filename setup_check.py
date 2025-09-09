#!/usr/bin/env python3
"""
FocusClass Tkinter - Setup Verification Script
Checks dependencies and system requirements
"""

import sys
import subprocess
import importlib
import platform
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


class SetupChecker:
    """Verify setup and dependencies for FocusClass Tkinter"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0
        
    def check_python_version(self):
        """Check Python version"""
        self.total_checks += 1
        version = sys.version_info
        
        print(f"🐍 Python Version: {version.major}.{version.minor}.{version.micro}")
        
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.errors.append("Python 3.8+ required. Current version is too old.")
            return False
        elif version.minor < 9:
            self.warnings.append("Python 3.9+ recommended for best performance.")
        
        self.success_count += 1
        return True
    
    def check_platform(self):
        """Check platform compatibility"""
        self.total_checks += 1
        system = platform.system()
        
        print(f"🖥️  Platform: {system} {platform.release()}")
        
        if system not in ["Windows", "Darwin", "Linux"]:
            self.warnings.append(f"Platform {system} may not be fully supported.")
        
        if system == "Windows":
            print("   ✅ Windows detected - Full focus mode available")
        else:
            print("   ⚠️  Non-Windows platform - Limited focus mode only")
            self.warnings.append("Full focus mode features require Windows.")
        
        self.success_count += 1
        return True
    
    def check_tkinter(self):
        """Check tkinter availability"""
        self.total_checks += 1
        
        try:
            import tkinter as tk
            import tkinter.ttk as ttk
            from tkinter import messagebox, filedialog, scrolledtext
            
            # Test tkinter functionality
            root = tk.Tk()
            root.withdraw()  # Hide the window
            root.destroy()
            
            print("✅ Tkinter: Available and functional")
            self.success_count += 1
            return True
            
        except ImportError as e:
            self.errors.append(f"Tkinter not available: {e}")
            print("❌ Tkinter: Not available")
            return False
        except Exception as e:
            self.errors.append(f"Tkinter test failed: {e}")
            print("❌ Tkinter: Test failed")
            return False
    
    def check_required_packages(self):
        """Check required Python packages"""
        required_packages = [
            ("websockets", "WebSocket communication"),
            ("aiohttp", "HTTP server functionality"),
            ("aiosqlite", "Async SQLite database"),
            ("mss", "Screen capture"),
            ("PIL", "Image processing (Pillow)"),
            ("psutil", "System monitoring"),
            ("qrcode", "QR code generation"),
        ]
        
        windows_packages = [
            ("win32api", "Windows API (pywin32)"),
            ("win32gui", "Windows GUI (pywin32)"),
            ("win32con", "Windows constants (pywin32)"),
        ]
        
        optional_packages = [
            ("aiortc", "WebRTC support (optional)"),
            ("zeroconf", "Network discovery (optional)"),
            ("cv2", "OpenCV (optional)"),
        ]
        
        # Check required packages
        print("\n📦 Required Packages:")
        for package, description in required_packages:
            self.total_checks += 1
            if self.check_package(package, description, required=True):
                self.success_count += 1
        
        # Check Windows-specific packages
        if platform.system() == "Windows":
            print("\n🪟 Windows-specific packages:")
            for package, description in windows_packages:
                self.total_checks += 1
                if self.check_package(package, description, required=True):
                    self.success_count += 1
        
        # Check optional packages
        print("\n🔧 Optional Packages:")
        for package, description in optional_packages:
            self.check_package(package, description, required=False)
    
    def check_package(self, package_name, description, required=True):
        """Check if a package is available"""
        try:
            importlib.import_module(package_name)
            print(f"   ✅ {package_name}: {description}")
            return True
        except ImportError:
            if required:
                print(f"   ❌ {package_name}: {description} - MISSING")
                self.errors.append(f"Required package '{package_name}' not found.")
                return False
            else:
                print(f"   ⚠️  {package_name}: {description} - Optional (not installed)")
                self.warnings.append(f"Optional package '{package_name}' not installed.")
                return False
    
    def check_directories(self):
        """Check and create required directories"""
        self.total_checks += 1
        
        print("\n📁 Directory Structure:")
        base_dir = Path(__file__).parent
        
        required_dirs = [
            "src",
            "src/common",
            "src/teacher", 
            "src/student",
            "logs",
            "assets",
            "exports"
        ]
        
        all_exist = True
        for dir_name in required_dirs:
            dir_path = base_dir / dir_name
            if dir_path.exists():
                print(f"   ✅ {dir_name}/")
            else:
                print(f"   ⚠️  {dir_name}/ - Creating...")
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    print(f"   ✅ {dir_name}/ - Created")
                except Exception as e:
                    print(f"   ❌ {dir_name}/ - Failed to create: {e}")
                    self.warnings.append(f"Could not create directory '{dir_name}'.")
                    all_exist = False
        
        if all_exist:
            self.success_count += 1
        
        return all_exist
    
    def check_permissions(self):
        """Check file permissions"""
        self.total_checks += 1
        
        print("\n🔐 Permissions:")
        base_dir = Path(__file__).parent
        
        # Test write permissions
        try:
            test_file = base_dir / "logs" / "test_permissions.tmp"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("test")
            test_file.unlink()
            print("   ✅ Write permissions: OK")
            self.success_count += 1
            return True
        except Exception as e:
            print(f"   ❌ Write permissions: Failed - {e}")
            self.errors.append("Insufficient write permissions for logs directory.")
            return False
    
    def check_network_ports(self):
        """Check if required network ports are available"""
        self.total_checks += 1
        
        print("\n🌐 Network Ports:")
        import socket
        
        ports_to_check = [8765, 8080]  # WebSocket and HTTP ports
        
        available_ports = []
        for port in ports_to_check:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    print(f"   ✅ Port {port}: Available")
                    available_ports.append(port)
            except socket.error:
                print(f"   ⚠️  Port {port}: In use (will try alternative)")
                self.warnings.append(f"Port {port} is in use. Application will try alternative ports.")
        
        if len(available_ports) > 0:
            self.success_count += 1
            return True
        else:
            self.errors.append("No default ports available. May need to configure alternative ports.")
            return False
    
    def install_missing_packages(self):
        """Offer to install missing packages"""
        if not self.errors:
            return True
        
        # Extract package names from error messages
        missing_packages = []
        for error in self.errors:
            if "not found" in error and "package" in error:
                # Extract package name from error message
                start = error.find("'") + 1
                end = error.find("'", start)
                if start > 0 and end > start:
                    package = error[start:end]
                    if package not in missing_packages:
                        missing_packages.append(package)
        
        if not missing_packages:
            return False
        
        print(f"\n🔧 Installing missing packages: {', '.join(missing_packages)}")
        
        # Map package names to pip install names
        pip_packages = {
            "PIL": "Pillow",
            "win32api": "pywin32",
            "win32gui": "pywin32", 
            "win32con": "pywin32",
            "cv2": "opencv-python"
        }
        
        install_list = []
        for package in missing_packages:
            pip_name = pip_packages.get(package, package)
            if pip_name not in install_list:
                install_list.append(pip_name)
        
        try:
            print("Running pip install...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--upgrade"
            ] + install_list)
            
            print("✅ Packages installed successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install packages: {e}")
            return False
        except Exception as e:
            print(f"❌ Installation error: {e}")
            return False
    
    def run_full_check(self, install_missing=False):
        """Run all checks"""
        print("🚀 FocusClass Tkinter - Setup Verification")
        print("=" * 50)
        
        # Basic system checks
        self.check_python_version()
        self.check_platform()
        self.check_tkinter()
        
        # Package checks
        self.check_required_packages()
        
        # Environment checks
        self.check_directories()
        self.check_permissions()
        self.check_network_ports()
        
        # Summary
        print("\n" + "=" * 50)
        print("📋 SETUP SUMMARY")
        print("=" * 50)
        
        print(f"✅ Successful checks: {self.success_count}/{self.total_checks}")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
        
        # Installation offer
        if install_missing and self.errors:
            print("\n🔧 AUTOMATIC FIX")
            print("=" * 20)
            if self.install_missing_packages():
                print("Rerun this script to verify the installation.")
                return False
        
        # Final verdict
        print("\n🎯 VERDICT")
        print("=" * 10)
        
        if not self.errors:
            print("✅ READY! FocusClass Tkinter is ready to run.")
            return True
        elif len(self.errors) <= 2 and len([e for e in self.errors if "optional" not in e.lower()]) == 0:
            print("⚠️  MOSTLY READY! Minor issues detected but application should work.")
            return True
        else:
            print("❌ NOT READY! Critical issues must be resolved before running.")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FocusClass Tkinter Setup Verification")
    parser.add_argument("--install", action="store_true", 
                       help="Automatically install missing packages")
    parser.add_argument("--gui", action="store_true",
                       help="Show GUI summary")
    
    args = parser.parse_args()
    
    checker = SetupChecker()
    
    try:
        ready = checker.run_full_check(install_missing=args.install)
        
        # Show GUI summary if requested
        if args.gui:
            show_gui_summary(checker, ready)
        
        # Exit with appropriate code
        sys.exit(0 if ready else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup check cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error during setup check: {e}")
        sys.exit(1)


def show_gui_summary(checker, ready):
    """Show GUI summary of setup check"""
    try:
        root = tk.Tk()
        root.title("FocusClass Setup Verification")
        root.geometry("600x400")
        
        # Create main frame
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_color = "green" if ready else "red"
        title_text = "✅ SETUP COMPLETE" if ready else "❌ SETUP ISSUES"
        
        title_label = tk.Label(main_frame, text=title_text, 
                              font=("Arial", 16, "bold"), 
                              fg=title_color)
        title_label.pack(pady=(0, 20))
        
        # Stats
        stats_text = f"Successful checks: {checker.success_count}/{checker.total_checks}"
        stats_label = tk.Label(main_frame, text=stats_text, font=("Arial", 12))
        stats_label.pack()
        
        # Scrollable text for details
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 9))
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add content
        if checker.errors:
            text_widget.insert(tk.END, "ERRORS:\n", "error")
            for error in checker.errors:
                text_widget.insert(tk.END, f"• {error}\n")
            text_widget.insert(tk.END, "\n")
        
        if checker.warnings:
            text_widget.insert(tk.END, "WARNINGS:\n", "warning")
            for warning in checker.warnings:
                text_widget.insert(tk.END, f"• {warning}\n")
            text_widget.insert(tk.END, "\n")
        
        if ready:
            text_widget.insert(tk.END, "🎉 Your system is ready to run FocusClass!\n\n")
            text_widget.insert(tk.END, "To start the application:\n")
            text_widget.insert(tk.END, "python main.py\n")
        
        # Configure tags
        text_widget.tag_configure("error", foreground="red", font=("Arial", 10, "bold"))
        text_widget.tag_configure("warning", foreground="orange", font=("Arial", 10, "bold"))
        
        text_widget.configure(state=tk.DISABLED)
        
        # Close button
        close_btn = tk.Button(main_frame, text="Close", command=root.destroy,
                             font=("Arial", 10))
        close_btn.pack(pady=(20, 0))
        
        root.mainloop()
        
    except Exception as e:
        print(f"Could not show GUI summary: {e}")


if __name__ == "__main__":
    main()