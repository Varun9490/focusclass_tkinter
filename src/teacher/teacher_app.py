"""
Teacher Application for FocusClass Tkinter - Main File
"""

import sys
import asyncio
import logging
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, List, Optional, Any
from pathlib import Path
import threading
from PIL import Image, ImageTk

# Import our modules
sys.path.append(str(Path(__file__).parent.parent))
from common.database_manager import DatabaseManager
from common.network_manager import NetworkManager, generate_session_code, generate_session_password
from common.screen_capture import ScreenCapture
from common.utils import (
    setup_logging, create_qr_code, get_local_ip, format_duration, 
    AsyncTkinterHelper, center_window, show_info_message, show_error_message, ask_yes_no
)
from common.config import *


class TeacherApp:
    """Main teacher application using tkinter"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = setup_logging("INFO", "logs/teacher.log")
        
        # Initialize async helper
        self.async_helper = AsyncTkinterHelper(root)
        self.async_helper.start_async_loop()
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.network_manager = NetworkManager(is_teacher=True)
        self.screen_capture = ScreenCapture()
        
        # Session state
        self.session_id = None
        self.session_active = False
        self.screen_sharing_active = False
        self.focus_mode_active = False
        self.session_start_time = 0
        
        # Student management
        self.connected_students = {}
        self.violation_throttle = {}
        self.violation_cooldown = 5.0
        
        # Setup UI and handlers
        self.setup_ui()
        self.setup_network_handlers()
        self.start_periodic_updates()
        
        self.logger.info("Teacher application initialized")
    
    def setup_ui(self):
        """Setup the main UI with responsive design"""
        self.root.title("FocusClass Teacher")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        self.root.configure(bg=TKINTER_THEME["bg_color"])
        
        # Configure root grid for responsiveness
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create main layout with responsive design
        self.create_main_layout()
        center_window(self.root, 1200, 800)
    
    def create_main_layout(self):
        """Create main layout"""
        # Main container
        main_frame = tk.Frame(self.root, bg=TKINTER_THEME["bg_color"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Session controls
        left_frame = tk.Frame(main_frame, bg=TKINTER_THEME["bg_color"], width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Session info group
        session_group = tk.LabelFrame(left_frame, text="Session Information", bg=TKINTER_THEME["bg_color"])
        session_group.pack(fill=tk.X, pady=5)
        
        # Session details
        self.session_code_var = tk.StringVar(value="Not Started")
        self.session_password_var = tk.StringVar(value="")
        self.teacher_ip_var = tk.StringVar(value=get_local_ip())
        
        tk.Label(session_group, text="Code:", bg=TKINTER_THEME["bg_color"]).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        tk.Label(session_group, textvariable=self.session_code_var, bg=TKINTER_THEME["bg_color"], font=("Arial", 12, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(session_group, text="Password:", bg=TKINTER_THEME["bg_color"]).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        tk.Label(session_group, textvariable=self.session_password_var, bg=TKINTER_THEME["bg_color"]).grid(row=1, column=1, sticky="w", padx=5)
        
        tk.Label(session_group, text="IP:", bg=TKINTER_THEME["bg_color"]).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        tk.Label(session_group, textvariable=self.teacher_ip_var, bg=TKINTER_THEME["bg_color"]).grid(row=2, column=1, sticky="w", padx=5)
        
        # QR Code
        self.qr_label = tk.Label(session_group, bg=TKINTER_THEME["bg_color"], text="QR Code")
        self.qr_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Control buttons
        controls_group = tk.LabelFrame(left_frame, text="Controls", bg=TKINTER_THEME["bg_color"])
        controls_group.pack(fill=tk.X, pady=5)
        
        self.start_btn = tk.Button(controls_group, text="📚 Start Session", command=self.start_session, 
                                  bg=TKINTER_THEME["success_color"], fg="white")
        self.start_btn.pack(fill=tk.X, padx=5, pady=2)
        
        self.screen_btn = tk.Button(controls_group, text="📺 Start Screen Sharing", command=self.start_screen_sharing,
                                   bg=TKINTER_THEME["accent_color"], fg="white", state=tk.DISABLED)
        self.screen_btn.pack(fill=tk.X, padx=5, pady=2)
        
        self.focus_btn = tk.Button(controls_group, text="🔒 Enable Focus Mode", command=self.enable_focus_mode,
                                  bg=TKINTER_THEME["warning_color"], fg="white", state=tk.DISABLED)
        self.focus_btn.pack(fill=tk.X, padx=5, pady=2)
        
        self.end_btn = tk.Button(controls_group, text="🛑 End Session", command=self.end_session,
                                bg=TKINTER_THEME["error_color"], fg="white", state=tk.DISABLED)
        self.end_btn.pack(fill=tk.X, padx=5, pady=2)
        
        # Right panel - Students and activities
        right_frame = tk.Frame(main_frame, bg=TKINTER_THEME["bg_color"])
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Notebook for tabs
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Students tab
        students_frame = tk.Frame(notebook, bg=TKINTER_THEME["bg_color"])
        notebook.add(students_frame, text="Students")
        
        tk.Label(students_frame, text="Connected Students", bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 14, "bold")).pack(pady=5)
        
        self.students_listbox = tk.Listbox(students_frame, bg="white", font=("Arial", 10))
        self.students_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Activities tab
        activities_frame = tk.Frame(notebook, bg=TKINTER_THEME["bg_color"])
        notebook.add(activities_frame, text="Activities")
        
        tk.Label(activities_frame, text="Violations & Activities", bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 14, "bold")).pack(pady=5)
        
        self.activities_text = scrolledtext.ScrolledText(activities_frame, height=25, bg="white", font=("Consolas", 9))
        self.activities_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Statistics tab
        stats_frame = tk.Frame(notebook, bg=TKINTER_THEME["bg_color"])
        notebook.add(stats_frame, text="Statistics")
        
        tk.Label(stats_frame, text="Session Statistics", bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 14, "bold")).pack(pady=5)
        
        stats_grid = tk.Frame(stats_frame, bg=TKINTER_THEME["bg_color"])
        stats_grid.pack(padx=20, pady=20)
        
        tk.Label(stats_grid, text="Duration:", bg=TKINTER_THEME["bg_color"]).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.duration_var = tk.StringVar(value="00:00:00")
        tk.Label(stats_grid, textvariable=self.duration_var, bg=TKINTER_THEME["bg_color"], font=("Arial", 12, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(stats_grid, text="Students:", bg=TKINTER_THEME["bg_color"]).grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.students_count_var = tk.StringVar(value="0")
        tk.Label(stats_grid, textvariable=self.students_count_var, bg=TKINTER_THEME["bg_color"], font=("Arial", 12, "bold")).grid(row=1, column=1, sticky="w", padx=5)
        
        tk.Label(stats_grid, text="Violations:", bg=TKINTER_THEME["bg_color"]).grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.violations_count_var = tk.StringVar(value="0")
        tk.Label(stats_grid, textvariable=self.violations_count_var, bg=TKINTER_THEME["bg_color"], font=("Arial", 12, "bold")).grid(row=2, column=1, sticky="w", padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, bd=1, 
                             bg=TKINTER_THEME["bg_color"], anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_network_handlers(self):
        """Setup network message handlers"""
        self.network_manager.register_message_handler("authenticate", self.handle_student_authentication)
        self.network_manager.register_message_handler("violation", self.handle_violation)
        self.network_manager.register_connection_handler("disconnection", self.handle_student_disconnection)
    
    def start_periodic_updates(self):
        """Start periodic UI updates"""
        def update():
            if self.session_active:
                # Update session duration
                duration = time.time() - self.session_start_time
                self.duration_var.set(format_duration(duration))
                
                # Update student count
                self.students_count_var.set(str(len(self.connected_students)))
            
            # Schedule next update
            self.root.after(1000, update)
        
        update()
    
    def start_session(self):
        """Start a new session"""
        threading.Thread(target=lambda: self.async_helper.run_async(self._start_session_async()), daemon=True).start()
    
    async def _start_session_async(self):
        """Async session start"""
        try:
            await self.db_manager.initialize_database()
            
            session_code = generate_session_code()
            password = generate_session_password()
            teacher_ip = get_local_ip()
            
            self.session_id = await self.db_manager.create_session(session_code, password, teacher_ip)
            server_info = await self.network_manager.start_teacher_server(session_code, password)
            
            self.session_active = True
            self.session_start_time = time.time()
            
            # Update UI
            self.root.after(0, self._update_session_ui, session_code, password, teacher_ip)
            self.logger.info(f"Session started: {session_code}")
            
        except Exception as e:
            self.logger.error(f"Failed to start session: {e}")
            self.root.after(0, lambda: show_error_message("Error", f"Failed to start session: {e}"))
    
    def _update_session_ui(self, session_code: str, password: str, teacher_ip: str):
        """Update UI with session information"""
        self.session_code_var.set(session_code)
        self.session_password_var.set(password)
        self.teacher_ip_var.set(teacher_ip)
        
        # Generate QR code
        try:
            qr_data = {"type": "focusclass_session", "teacher_ip": teacher_ip, "session_code": session_code, "password": password}
            qr_image = create_qr_code(qr_data, size=150)
            qr_photo = ImageTk.PhotoImage(qr_image)
            self.qr_label.configure(image=qr_photo, text="")
            self.qr_label.image = qr_photo
        except Exception as e:
            self.logger.error(f"Failed to generate QR code: {e}")
        
        # Update buttons
        self.start_btn.configure(state=tk.DISABLED)
        self.screen_btn.configure(state=tk.NORMAL)
        self.focus_btn.configure(state=tk.NORMAL)
        self.end_btn.configure(state=tk.NORMAL)
        self.status_var.set(f"Session Active: {session_code}")
    
    def end_session(self):
        """End current session"""
        if ask_yes_no("Confirm", "End the session?"):
            threading.Thread(target=lambda: self.async_helper.run_async(self._end_session_async()), daemon=True).start()
    
    async def _end_session_async(self):
        """Async session end"""
        try:
            if self.session_id:
                await self.db_manager.end_session(self.session_id)
            await self.network_manager.stop_server()
            if self.screen_sharing_active:
                self.screen_capture.stop_capture()
            
            self.session_active = False
            self.screen_sharing_active = False
            self.focus_mode_active = False
            
            self.root.after(0, self._reset_session_ui)
            self.logger.info("Session ended")
            
        except Exception as e:
            self.logger.error(f"Error ending session: {e}")
    
    def _reset_session_ui(self):
        """Reset UI to initial state"""
        self.session_code_var.set("Not Started")
        self.session_password_var.set("")
        
        # Reset QR code
        self.qr_label.configure(image="", text="QR Code\n(Start session to generate)")
        if hasattr(self.qr_label, 'image'):
            delattr(self.qr_label, 'image')  # Remove image reference
        
        self.start_btn.configure(state=tk.NORMAL)
        self.screen_btn.configure(state=tk.DISABLED, text="📺 Start Screen Sharing")
        self.focus_btn.configure(state=tk.DISABLED, text="🔒 Enable Focus Mode")
        self.end_btn.configure(state=tk.DISABLED)
        
        self.students_listbox.delete(0, tk.END)
        self.activities_text.config(state=tk.NORMAL)
        self.activities_text.delete(1.0, tk.END)
        self.activities_text.config(state=tk.DISABLED)
        self.status_var.set("Ready - Start a session to begin")
    
    def start_screen_sharing(self):
        """Start screen sharing"""
        if not self.session_active:
            show_error_message("Error", "Start a session first")
            return
        
        try:
            self.screen_capture.set_quality("medium")
            success = self.screen_capture.start_tkinter_capture(0)
            
            if success:
                self.screen_sharing_active = True
                self.screen_btn.configure(text="📺 Stop Screen Sharing", command=self.stop_screen_sharing, bg=TKINTER_THEME["error_color"])
                self.status_var.set("Screen sharing active")
                self.logger.info("Screen sharing started")
            else:
                show_error_message("Error", "Failed to start screen sharing")
                
        except Exception as e:
            show_error_message("Error", f"Failed to start screen sharing: {e}")
    
    def stop_screen_sharing(self):
        """Stop screen sharing"""
        self.screen_capture.stop_capture()
        self.screen_sharing_active = False
        self.screen_btn.configure(text="📺 Start Screen Sharing", command=self.start_screen_sharing, bg=TKINTER_THEME["accent_color"])
        self.status_var.set("Screen sharing stopped")
    
    def enable_focus_mode(self):
        """Enable focus mode"""
        threading.Thread(target=lambda: self.async_helper.run_async(self._enable_focus_mode_async()), daemon=True).start()
    
    async def _enable_focus_mode_async(self):
        """Async focus mode enable"""
        try:
            await self.network_manager.broadcast_message("enable_focus_mode", {"enabled": True})
            if self.session_id:
                await self.db_manager.update_focus_mode(self.session_id, True)
            
            self.focus_mode_active = True
            self.root.after(0, lambda: self.focus_btn.configure(text="🔓 Disable Focus Mode", command=self.disable_focus_mode, bg=TKINTER_THEME["error_color"]))
            self.root.after(0, lambda: self.status_var.set("Focus mode enabled"))
            
        except Exception as e:
            self.logger.error(f"Error enabling focus mode: {e}")
    
    def disable_focus_mode(self):
        """Disable focus mode"""
        threading.Thread(target=lambda: self.async_helper.run_async(self._disable_focus_mode_async()), daemon=True).start()
    
    async def _disable_focus_mode_async(self):
        """Async focus mode disable"""
        try:
            await self.network_manager.broadcast_message("disable_focus_mode", {"enabled": False})
            if self.session_id:
                await self.db_manager.update_focus_mode(self.session_id, False)
            
            self.focus_mode_active = False
            self.root.after(0, lambda: self.focus_btn.configure(text="🔒 Enable Focus Mode", command=self.enable_focus_mode, bg=TKINTER_THEME["warning_color"]))
            self.root.after(0, lambda: self.status_var.set("Focus mode disabled"))
            
        except Exception as e:
            self.logger.error(f"Error disabling focus mode: {e}")
    
    async def handle_student_authentication(self, client_id: str, data: dict):
        """Handle student authentication"""
        try:
            student_name = data.get("student_name", "Unknown")
            student_ip = self.network_manager.get_client_ip(client_id)
            
            if self.session_id:
                student_id = await self.db_manager.add_student(self.session_id, student_name, student_ip)
                self.connected_students[client_id] = {"student_id": student_id, "name": student_name, "ip": student_ip}
            
            self.root.after(0, self._update_students_list)
            self.root.after(0, lambda: self._add_activity_log(f"✅ {student_name} ({student_ip}) connected"))
            
        except Exception as e:
            self.logger.error(f"Error handling authentication: {e}")
    
    async def handle_student_disconnection(self, client_id: str):
        """Handle student disconnection"""
        try:
            if client_id in self.connected_students:
                student_info = self.connected_students[client_id]
                await self.db_manager.remove_student(student_info["student_id"])
                
                self.root.after(0, lambda: self._add_activity_log(f"❌ {student_info['name']} disconnected"))
                del self.connected_students[client_id]
                self.root.after(0, self._update_students_list)
                
        except Exception as e:
            self.logger.error(f"Error handling disconnection: {e}")
    
    async def handle_violation(self, client_id: str, data: dict):
        """Handle focus violation with throttling"""
        try:
            if client_id not in self.connected_students:
                return
            
            student_name = self.connected_students[client_id]["name"]
            violation_type = data.get("type", "unknown")
            description = data.get("description", "")
            
            # Simple throttling
            current_time = time.time()
            throttle_key = f"{client_id}_{violation_type}"
            
            if throttle_key in self.violation_throttle:
                last_time, count = self.violation_throttle[throttle_key]
                if current_time - last_time < self.violation_cooldown:
                    if count >= 3:
                        return  # Silent increment
                    else:
                        self.violation_throttle[throttle_key] = (last_time, count + 1)
                else:
                    self.violation_throttle[throttle_key] = (current_time, 1)
            else:
                self.violation_throttle[throttle_key] = (current_time, 1)
            
            # Log violation
            if self.session_id:
                await self.db_manager.log_violation(self.session_id, self.connected_students[client_id]["student_id"], violation_type, description)
            
            # Update UI
            count = self.violation_throttle[throttle_key][1]
            display_desc = description
            if count > 1:
                display_desc += f" (x{count})"
            
            self.root.after(0, lambda: self._add_activity_log(f"⚠️ {student_name}: {violation_type} - {display_desc}"))
            
        except Exception as e:
            self.logger.error(f"Error handling violation: {e}")
    
    def _update_students_list(self):
        """Update students list in UI"""
        self.students_listbox.delete(0, tk.END)
        for student_info in self.connected_students.values():
            self.students_listbox.insert(tk.END, f"{student_info['name']} ({student_info['ip']})")
    
    def _add_activity_log(self, message: str):
        """Add activity log message"""
        timestamp = time.strftime("%H:%M:%S")
        self.activities_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.activities_text.see(tk.END)
        
        # Keep only last 100 lines
        lines = self.activities_text.get(1.0, tk.END).splitlines()
        if len(lines) > 100:
            self.activities_text.delete(1.0, f"{len(lines) - 100}.0")
    
    def clear_activity_log(self):
        """Clear the activity log"""
        try:
            self.activities_text.config(state=tk.NORMAL)
            self.activities_text.delete(1.0, tk.END)
            self.activities_text.config(state=tk.DISABLED)
            self.logger.info("Activity log cleared")
        except Exception as e:
            self.logger.error(f"Error clearing activity log: {e}")
    
    def export_session_data(self):
        """Export session data"""
        if not self.session_active:
            show_error_message("Export Error", "No active session to export")
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                title="Export Session Data",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                # Export session data
                export_data = f"""FocusClass Session Export
=========================
Session Code: {self.session_code_var.get()}
Duration: {self.duration_var.get()}
Students: {self.students_count_var.get()}
Violations: {self.violations_count_var.get()}

Activity Log:
{self.activities_text.get(1.0, tk.END)}"""
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(export_data)
                
                show_info_message("Export Complete", f"Session data exported to {filename}")
                
        except Exception as e:
            self.logger.error(f"Export error: {e}")
            show_error_message("Export Error", f"Failed to export data: {e}")
    
    def run(self):
        """Run the teacher application"""
        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in teacher app main loop: {e}")
        finally:
            # Clean shutdown
            if self.async_helper:
                self.async_helper.stop()


def main():
    """Main entry point for teacher application"""
    try:
        root = tk.Tk()
        app = TeacherApp(root)
        app.run()
    except Exception as e:
        print(f"Error starting teacher application: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()