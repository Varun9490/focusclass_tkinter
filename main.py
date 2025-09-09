"""
FocusClass Tkinter Main Launcher
Entry point for the tkinter version of FocusClass
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import subprocess
import threading
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.common.utils import setup_logging, center_window, show_error_message, show_info_message
from src.common.config import *


class FocusClassLauncher:
    """Main launcher for FocusClass Tkinter application"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = setup_logging("INFO", "logs/launcher.log")
        
        # Configure root window
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.resizable(True, True)
        self.root.minsize(600, 400)
        
        # State tracking
        self.is_running = True
        
        try:
            self.setup_ui()
            self.logger.info("FocusClass Launcher initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize launcher: {e}")
            show_error_message("Initialization Error", f"Failed to start FocusClass:\n\n{e}")
            self.root.destroy()
    
    def setup_ui(self):
        """Setup the launcher UI"""
        self.root.title("FocusClass - Classroom Management System")
        self.root.geometry("700x500")
        self.root.configure(bg=TKINTER_THEME["bg_color"])
        
        # Make window responsive
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Main container with responsive layout
        main_frame = tk.Frame(self.root, bg=TKINTER_THEME["bg_color"])
        main_frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        main_frame.grid_rowconfigure(1, weight=1)  # Description area can expand
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title section
        title_frame = tk.Frame(main_frame, bg=TKINTER_THEME["bg_color"])
        title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        title_label = tk.Label(title_frame, text="FocusClass", 
                              bg=TKINTER_THEME["bg_color"], 
                              fg=TKINTER_THEME["accent_color"],
                              font=(TKINTER_THEME["font_family"], 28, "bold"))
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Classroom Management System (Tkinter Edition)", 
                                 bg=TKINTER_THEME["bg_color"], 
                                 fg=TKINTER_THEME["fg_color"],
                                 font=(TKINTER_THEME["font_family"], 12))
        subtitle_label.pack(pady=(5, 0))
        
        # Description section with scrollable text
        desc_frame = tk.Frame(main_frame, bg=TKINTER_THEME["bg_color"])
        desc_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 20))
        desc_frame.grid_rowconfigure(1, weight=1)
        desc_frame.grid_columnconfigure(0, weight=1)
        
        desc_title = tk.Label(desc_frame, text="Features:", 
                             bg=TKINTER_THEME["bg_color"], 
                             fg=TKINTER_THEME["fg_color"],
                             font=(TKINTER_THEME["font_family"], 12, "bold"))
        desc_title.grid(row=0, column=0, sticky="w")
        
        # Scrollable description
        desc_text_widget = tk.Text(desc_frame, 
                                  bg="white", 
                                  fg=TKINTER_THEME["fg_color"],
                                  font=(TKINTER_THEME["font_family"], 10),
                                  wrap=tk.WORD, 
                                  height=8,
                                  relief=tk.FLAT,
                                  state=tk.DISABLED)
        desc_text_widget.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        
        desc_scrollbar = tk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=desc_text_widget.yview)
        desc_scrollbar.grid(row=1, column=1, sticky="ns")
        desc_text_widget.config(yscrollcommand=desc_scrollbar.set)
        
        # Add feature descriptions
        desc_text = """• Real-time student monitoring and screen sharing
• Focus mode to prevent distractions and unauthorized apps
• Violation tracking and detailed reporting
• Session management with QR code connectivity
• Network-based communication between teacher and students
• Database logging for session analytics
• Cross-platform compatibility (Windows focus mode)
• Lightweight design with minimal system requirements
• Secure session authentication and encryption
• Export capabilities for session reports"""
        
        desc_text_widget.config(state=tk.NORMAL)
        desc_text_widget.insert(1.0, desc_text)
        desc_text_widget.config(state=tk.DISABLED)
        
        # Mode selection section
        mode_frame = tk.Frame(main_frame, bg=TKINTER_THEME["bg_color"])
        mode_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        mode_frame.grid_columnconfigure((0, 1), weight=1)
        
        tk.Label(mode_frame, text="Select Mode:", 
                bg=TKINTER_THEME["bg_color"], 
                fg=TKINTER_THEME["fg_color"],
                font=(TKINTER_THEME["font_family"], 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Teacher button with improved styling
        self.teacher_btn = tk.Button(mode_frame, text="👨‍🏫 Teacher Mode", 
                                    command=self.launch_teacher,
                                    bg=TKINTER_THEME["accent_color"], 
                                    fg="white",
                                    font=(TKINTER_THEME["font_family"], 12, "bold"),
                                    relief=tk.RAISED,
                                    bd=2,
                                    cursor="hand2")
        self.teacher_btn.grid(row=1, column=0, padx=(0, 10), pady=5, sticky="ew")
        
        # Student button with improved styling
        self.student_btn = tk.Button(mode_frame, text="👨‍🎓 Student Mode", 
                                    command=self.launch_student,
                                    bg=TKINTER_THEME["success_color"], 
                                    fg="white",
                                    font=(TKINTER_THEME["font_family"], 12, "bold"),
                                    relief=tk.RAISED,
                                    bd=2,
                                    cursor="hand2")
        self.student_btn.grid(row=1, column=1, padx=(10, 0), pady=5, sticky="ew")
        
        # Add hover effects
        self._setup_button_hover_effects()
        
        # Version and control info
        version_frame = tk.Frame(main_frame, bg=TKINTER_THEME["bg_color"])
        version_frame.grid(row=3, column=0, sticky="ew")
        version_frame.grid_columnconfigure(1, weight=1)
        
        tk.Label(version_frame, text=f"Version {APP_VERSION} - Tkinter Edition", 
                bg=TKINTER_THEME["bg_color"], 
                fg=TKINTER_THEME["fg_color"],
                font=(TKINTER_THEME["font_family"], 9)).grid(row=0, column=0, sticky="w")
        
        # Control buttons
        control_frame = tk.Frame(version_frame, bg=TKINTER_THEME["bg_color"])
        control_frame.grid(row=0, column=2, sticky="e")
        
        # Setup check button
        setup_btn = tk.Button(control_frame, text="Setup Check", command=self.run_setup_check,
                             bg=TKINTER_THEME["bg_color"], 
                             fg=TKINTER_THEME["accent_color"],
                             relief=tk.FLAT,
                             font=(TKINTER_THEME["font_family"], 9),
                             cursor="hand2")
        setup_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # About button
        about_btn = tk.Button(control_frame, text="About", command=self.show_about,
                             bg=TKINTER_THEME["bg_color"], 
                             fg=TKINTER_THEME["accent_color"],
                             relief=tk.FLAT,
                             font=(TKINTER_THEME["font_family"], 9),
                             cursor="hand2")
        about_btn.pack(side=tk.RIGHT)
        
        center_window(self.root, 700, 500)
    
    def launch_teacher(self):
        """Launch teacher application with improved error handling"""
        try:
            self.logger.info("Launching teacher application...")
            
            # Disable buttons to prevent multiple launches
            self.teacher_btn.config(state=tk.DISABLED, text="Launching...")
            self.student_btn.config(state=tk.DISABLED)
            self.root.update()
            
            # Import and validate teacher app
            try:
                from src.teacher.teacher_app import TeacherApp
            except ImportError as e:
                raise ImportError(f"Failed to import teacher application: {e}")
            
            # Close launcher
            self.is_running = False
            self.root.withdraw()  # Hide instead of destroy for better error handling
            
            # Create new root for teacher app
            teacher_root = tk.Tk()
            try:
                app = TeacherApp(teacher_root)
                app.run()
            except Exception as e:
                # If teacher app fails, show launcher again
                self.root.deiconify()
                raise e
            finally:
                # Clean shutdown
                try:
                    teacher_root.destroy()
                except:
                    pass
                if self.is_running:
                    self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error launching teacher app: {e}")
            # Re-enable buttons
            self.teacher_btn.config(state=tk.NORMAL, text="👨‍🏫 Teacher Mode")
            self.student_btn.config(state=tk.NORMAL)
            show_error_message("Launch Error", f"Failed to launch teacher application:\n\n{str(e)}\n\nPlease check the logs for more details.")
    
    def launch_student(self):
        """Launch student application with improved error handling"""
        try:
            self.logger.info("Launching student application...")
            
            # Disable buttons to prevent multiple launches
            self.student_btn.config(state=tk.DISABLED, text="Launching...")
            self.teacher_btn.config(state=tk.DISABLED)
            self.root.update()
            
            # Import and validate student app
            try:
                from src.student.student_app import StudentApp
            except ImportError as e:
                raise ImportError(f"Failed to import student application: {e}")
            
            # Close launcher
            self.is_running = False
            self.root.withdraw()  # Hide instead of destroy for better error handling
            
            # Create new root for student app
            student_root = tk.Tk()
            try:
                app = StudentApp(student_root)
                app.run()
            except Exception as e:
                # If student app fails, show launcher again
                self.root.deiconify()
                raise e
            finally:
                # Clean shutdown
                try:
                    student_root.destroy()
                except:
                    pass
                if self.is_running:
                    self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error launching student app: {e}")
            # Re-enable buttons
            self.student_btn.config(state=tk.NORMAL, text="👨‍🎓 Student Mode")
            self.teacher_btn.config(state=tk.NORMAL)
            show_error_message("Launch Error", f"Failed to launch student application:\n\n{str(e)}\n\nPlease check the logs for more details.")
    
    def show_about(self):
        """Show about dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About FocusClass")
        about_window.geometry("500x350")
        about_window.configure(bg=TKINTER_THEME["bg_color"])
        about_window.transient(self.root)
        about_window.grab_set()
        center_window(about_window, 600, 450)
        
        # About content
        about_frame = tk.Frame(about_window, bg=TKINTER_THEME["bg_color"])
        about_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        tk.Label(about_frame, text="FocusClass", 
                bg=TKINTER_THEME["bg_color"], 
                fg=TKINTER_THEME["accent_color"],
                font=(TKINTER_THEME["font_family"], 18, "bold")).pack(pady=(0, 10))
        
        # Version
        tk.Label(about_frame, text=f"Version {APP_VERSION} - Tkinter Edition", 
                bg=TKINTER_THEME["bg_color"], 
                fg=TKINTER_THEME["fg_color"],
                font=(TKINTER_THEME["font_family"], 12)).pack(pady=(0, 20))
        
        # Description
        about_text = """FocusClass is a comprehensive classroom management system designed to help teachers maintain focus and monitor student activities during digital learning sessions.

Key Features:
• Real-time student monitoring
• Screen sharing and capture
• Focus mode enforcement
• Violation tracking and reporting
• QR code session connectivity
• Network-based communication
• Session analytics and export

Technology Stack:
• Python 3.x
• Tkinter GUI framework
• WebSocket communication
• SQLite database
• MSS screen capture
• Asyncio for concurrency

This tkinter edition provides a lightweight, cross-platform alternative to the PyQt5 version while maintaining all core functionality."""
        
        text_widget = tk.Text(about_frame, bg="white", fg=TKINTER_THEME["fg_color"],
                             font=(TKINTER_THEME["font_family"], 9),
                             wrap=tk.WORD, height=15, width=60)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(1.0, about_text)
        text_widget.configure(state=tk.DISABLED)
        
        # Scrollbar for text
        scrollbar = tk.Scrollbar(text_widget)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)
        
        # Close button
        tk.Button(about_frame, text="Close", command=about_window.destroy,
                 bg=TKINTER_THEME["accent_color"], fg="white",
                 font=(TKINTER_THEME["font_family"], 10)).pack(pady=(10, 0))
    
    def _setup_button_hover_effects(self):
        """Setup hover effects for buttons"""
        def on_enter_teacher(e):
            if self.teacher_btn['state'] != tk.DISABLED:
                self.teacher_btn.config(bg="#0056b3")
        
        def on_leave_teacher(e):
            if self.teacher_btn['state'] != tk.DISABLED:
                self.teacher_btn.config(bg=TKINTER_THEME["accent_color"])
        
        def on_enter_student(e):
            if self.student_btn['state'] != tk.DISABLED:
                self.student_btn.config(bg="#218838")
        
        def on_leave_student(e):
            if self.student_btn['state'] != tk.DISABLED:
                self.student_btn.config(bg=TKINTER_THEME["success_color"])
        
        self.teacher_btn.bind("<Enter>", on_enter_teacher)
        self.teacher_btn.bind("<Leave>", on_leave_teacher)
        self.student_btn.bind("<Enter>", on_enter_student)
        self.student_btn.bind("<Leave>", on_leave_student)
    
    def run_setup_check(self):
        """Run setup verification"""
        try:
            import subprocess
            import sys
            
            # Run setup check with GUI
            setup_script = Path(__file__).parent / "setup_check.py"
            if setup_script.exists():
                subprocess.run([sys.executable, str(setup_script), "--gui"], 
                             cwd=Path(__file__).parent)
            else:
                show_error_message("Setup Check", "setup_check.py not found")
                
        except Exception as e:
            self.logger.error(f"Error running setup check: {e}")
            show_error_message("Setup Check Error", f"Failed to run setup check: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        try:
            self.logger.info("FocusClass Launcher shutting down")
            self.is_running = False
            self.root.destroy()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    def run(self):
        """Run the launcher with error handling"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("Launcher interrupted by user")
        except Exception as e:
            self.logger.error(f"Unexpected error in launcher: {e}")
            show_error_message("Runtime Error", f"An unexpected error occurred:\n\n{e}")
        finally:
            self.is_running = False


def main():
    """Main entry point with comprehensive error handling"""
    try:
        # Ensure required directories exist
        base_dir = Path(__file__).parent
        for directory in ["logs", "assets", "exports"]:
            (base_dir / directory).mkdir(exist_ok=True)
        
        # Setup logging first
        logger = setup_logging("INFO", "logs/launcher.log")
        logger.info("Starting FocusClass Tkinter Launcher")
        
        # Check dependencies
        try:
            check_dependencies()
            logger.info("Dependency check passed")
        except Exception as e:
            logger.error(f"Dependency check failed: {e}")
            # Try to show error dialog
            try:
                root = tk.Tk()
                root.withdraw()
                show_error_message("Dependency Error", 
                                 f"Missing required dependencies:\n\n{e}\n\nRun 'python setup_check.py --install' to fix this.")
                root.destroy()
            except:
                print(f"Dependency Error: {e}")
                print("Run 'python setup_check.py --install' to install missing dependencies.")
            return
        
        # Create and run launcher
        root = tk.Tk()
        try:
            launcher = FocusClassLauncher(root)
            launcher.run()
        except Exception as e:
            logger.error(f"Launcher error: {e}")
            raise
        finally:
            try:
                root.destroy()
            except:
                pass
        
        logger.info("FocusClass Launcher shutdown complete")
        
    except KeyboardInterrupt:
        print("\nFocusClass startup cancelled by user.")
    except Exception as e:
        error_msg = f"Failed to start FocusClass: {e}"
        print(error_msg)
        
        # Try to show GUI error
        try:
            root = tk.Tk()
            root.withdraw()
            show_error_message("Startup Error", f"Failed to start FocusClass:\n\n{e}\n\nCheck logs/launcher.log for details.")
            root.destroy()
        except:
            pass  # GUI not available


def check_dependencies():
    """Check if required dependencies are available"""
    missing_deps = []
    
    try:
        import websockets
    except ImportError:
        missing_deps.append("websockets")
    
    try:
        import aiohttp
    except ImportError:
        missing_deps.append("aiohttp")
    
    try:
        import mss
    except ImportError:
        missing_deps.append("mss")
    
    try:
        import PIL
    except ImportError:
        missing_deps.append("Pillow")
    
    try:
        import psutil
    except ImportError:
        missing_deps.append("psutil")
    
    try:
        import qrcode
    except ImportError:
        missing_deps.append("qrcode")
    
    if missing_deps:
        dep_list = "\n".join(f"• {dep}" for dep in missing_deps)
        error_msg = f"""Missing required dependencies:

{dep_list}

Please install them using:
pip install {' '.join(missing_deps)}"""
        
        raise ImportError(error_msg)


if __name__ == "__main__":
    main()