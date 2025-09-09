"""
Student Application for FocusClass Tkinter
Main GUI and functionality for the student using tkinter
"""

import sys
import asyncio
import logging
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Optional
from pathlib import Path
import threading
import psutil

# Import our modules
sys.path.append(str(Path(__file__).parent.parent))
from common.network_manager import NetworkManager
from common.screen_capture import StudentScreenShare
from common.focus_manager import FocusManager, LightweightFocusManager, is_admin
from common.utils import (
    setup_logging, parse_qr_code_data, format_duration, AsyncTkinterHelper, 
    center_window, show_error_message, ask_yes_no
)
from common.config import *


class StudentApp:
    """Main student application using tkinter"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.logger = setup_logging("INFO", "logs/student.log")
        
        # Initialize components
        self.network_manager = NetworkManager(is_teacher=False)
        
        # Initialize focus manager
        if is_admin():
            self.focus_manager = FocusManager(violation_callback=self.handle_focus_violation)
        else:
            self.focus_manager = LightweightFocusManager(violation_callback=self.handle_focus_violation)
            
        self.screen_share = StudentScreenShare(approval_callback=self.handle_screen_share_request)
        
        # State
        self.connected = False
        self.student_name = ""
        self.focus_mode_active = False
        self.connection_start_time = 0
        self.violation_count = 0
        
        # Setup UI and handlers
        self.setup_ui()
        self.setup_network_handlers()
        self.start_monitoring()
        
        self.logger.info("Student application initialized")
    
    def setup_ui(self):
        """Setup the main UI with responsive design"""
        self.root.title("FocusClass Student")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        self.root.configure(bg=TKINTER_THEME["bg_color"])
        
        # Configure root for responsiveness
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)  # Status bar
        self.root.grid_columnconfigure(0, weight=1)
        
        # Main container with grid layout
        main_frame = tk.Frame(self.root, bg=TKINTER_THEME["bg_color"])
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)  # Activity log expands
        
        # Connection panel with improved layout
        conn_group = tk.LabelFrame(main_frame, text="Connection Settings", 
                                  bg=TKINTER_THEME["bg_color"],
                                  font=(TKINTER_THEME["font_family"], 11, "bold"))
        conn_group.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        conn_group.grid_columnconfigure((1, 3), weight=1)
        
        form_frame = tk.Frame(conn_group, bg=TKINTER_THEME["bg_color"])
        form_frame.pack(padx=10, pady=10)
        
        # Form fields
        tk.Label(form_frame, text="Name:", bg=TKINTER_THEME["bg_color"]).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.name_entry = tk.Entry(form_frame, width=15)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)
        self.name_entry.insert(0, "Student")
        
        tk.Label(form_frame, text="Teacher IP:", bg=TKINTER_THEME["bg_color"]).grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.teacher_ip_entry = tk.Entry(form_frame, width=15)
        self.teacher_ip_entry.grid(row=0, column=3, padx=5, pady=2)
        
        tk.Label(form_frame, text="Code:", bg=TKINTER_THEME["bg_color"]).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.session_code_entry = tk.Entry(form_frame, width=15)
        self.session_code_entry.grid(row=1, column=1, padx=5, pady=2)
        
        tk.Label(form_frame, text="Password:", bg=TKINTER_THEME["bg_color"]).grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.password_entry = tk.Entry(form_frame, width=15, show="*")
        self.password_entry.grid(row=1, column=3, padx=5, pady=2)
        
        # Buttons
        btn_frame = tk.Frame(conn_group, bg=TKINTER_THEME["bg_color"])
        btn_frame.pack(pady=5)
        
        self.connect_btn = tk.Button(btn_frame, text="🔗 Connect", command=self.connect_to_teacher,
                                    bg=TKINTER_THEME["success_color"], fg="white")
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.disconnect_btn = tk.Button(btn_frame, text="❌ Disconnect", command=self.disconnect_from_teacher,
                                       bg=TKINTER_THEME["error_color"], fg="white", state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)
        
        # Status panel with improved layout
        status_group = tk.LabelFrame(main_frame, text="Status", 
                                    bg=TKINTER_THEME["bg_color"],
                                    font=(TKINTER_THEME["font_family"], 11, "bold"))
        status_group.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        status_group.grid_columnconfigure((1, 3), weight=1)
        
        status_grid = tk.Frame(status_group, bg=TKINTER_THEME["bg_color"])
        status_grid.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        status_group.grid_columnconfigure(0, weight=1)
        
        tk.Label(status_grid, text="Status:", bg=TKINTER_THEME["bg_color"]).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.connection_status_var = tk.StringVar(value="Disconnected")
        tk.Label(status_grid, textvariable=self.connection_status_var, bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 10, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(status_grid, text="Connected Time:", bg=TKINTER_THEME["bg_color"]).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.connected_time_var = tk.StringVar(value="00:00:00")
        tk.Label(status_grid, textvariable=self.connected_time_var, bg=TKINTER_THEME["bg_color"]).grid(row=1, column=1, sticky="w", padx=5)
        
        tk.Label(status_grid, text="Focus Mode:", bg=TKINTER_THEME["bg_color"]).grid(row=0, column=2, sticky="w", padx=20, pady=2)
        self.focus_mode_var = tk.StringVar(value="Disabled")
        tk.Label(status_grid, textvariable=self.focus_mode_var, bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 10, "bold")).grid(row=0, column=3, sticky="w", padx=5)
        
        tk.Label(status_grid, text="Violations:", bg=TKINTER_THEME["bg_color"]).grid(row=1, column=2, sticky="w", padx=20, pady=2)
        self.violation_count_var = tk.StringVar(value="0")
        tk.Label(status_grid, textvariable=self.violation_count_var, bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 10, "bold")).grid(row=1, column=3, sticky="w", padx=5)
        
        # Battery info
        tk.Label(status_grid, text="Battery:", bg=TKINTER_THEME["bg_color"]).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.battery_var = tk.StringVar(value="Unknown")
        tk.Label(status_grid, textvariable=self.battery_var, bg=TKINTER_THEME["bg_color"]).grid(row=2, column=1, sticky="w", padx=5)
        
        # Activity log with improved layout
        activity_group = tk.LabelFrame(main_frame, text="Activity Log", 
                                      bg=TKINTER_THEME["bg_color"],
                                      font=(TKINTER_THEME["font_family"], 11, "bold"))
        activity_group.grid(row=2, column=0, sticky="nsew")
        
        self.activity_text = scrolledtext.ScrolledText(activity_group, height=15, 
                                                      bg="white", 
                                                      fg=TKINTER_THEME["fg_color"],
                                                      font=("Consolas", 9))
        self.activity_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        activity_group.grid_rowconfigure(0, weight=1)
        activity_group.grid_columnconfigure(0, weight=1)
        
        # Status bar with grid layout
        self.status_var = tk.StringVar(value="Not connected")
        status_bar = tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, bd=1,
                             bg=TKINTER_THEME["bg_color"], anchor=tk.W)
        status_bar.grid(row=1, column=0, sticky="ew")
        
        center_window(self.root, 900, 700)
    
    def setup_network_handlers(self):
        """Setup network message handlers"""
        self.network_manager.register_message_handler("auth_success", self.handle_auth_success)
        self.network_manager.register_message_handler("enable_focus_mode", self.handle_enable_focus_mode)
        self.network_manager.register_message_handler("disable_focus_mode", self.handle_disable_focus_mode)
        self.network_manager.register_connection_handler("disconnection", self.handle_disconnection)
    
    def start_monitoring(self):
        """Start system monitoring"""
        def monitor():
            try:
                if self.connected:
                    duration = time.time() - self.connection_start_time
                    self.connected_time_var.set(format_duration(duration))
                
                # Update battery info
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        percent = battery.percent
                        plugged = "Charging" if battery.power_plugged else "Not charging"
                        self.battery_var.set(f"{percent}% ({plugged})")
                        
                        # Check for low battery violation
                        if percent < 20 and not battery.power_plugged and self.connected:
                            def run_async_task():
                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    loop.run_until_complete(self._send_violation("low_battery", f"Low battery: {percent}% (not charging)"))
                                finally:
                                    loop.close()
                            threading.Thread(target=run_async_task, daemon=True).start()
                    else:
                        self.battery_var.set("No battery")
                except:
                    self.battery_var.set("Unknown")
                    
            except Exception as e:
                self.logger.error(f"Error in monitoring: {e}")
            
            self.root.after(5000, monitor)
        
        monitor()
    
    def connect_to_teacher(self):
        """Connect to teacher"""
        student_name = self.name_entry.get().strip()
        teacher_ip = self.teacher_ip_entry.get().strip()
        session_code = self.session_code_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not all([student_name, teacher_ip, session_code, password]):
            show_error_message("Error", "Please fill in all fields")
            return
        
        self.student_name = student_name
        def run_async_task():
            error_message = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._connect_async(teacher_ip, session_code, password, student_name))
            except Exception as e:
                error_message = str(e)
                self.logger.error(f"Error in connection task: {e}")
            finally:
                loop.close()
                if error_message:
                    self.root.after(0, lambda msg=error_message: show_error_message("Connection Error", f"Failed to connect: {msg}"))
        
        threading.Thread(target=run_async_task, daemon=True).start()
    
    async def _connect_async(self, teacher_ip: str, session_code: str, password: str, student_name: str):
        """Async connection to teacher"""
        try:
            success = await self.network_manager.connect_to_teacher(teacher_ip, session_code, password, student_name)
            
            if success:
                self.connected = True
                self.connection_start_time = time.time()
                self.root.after(0, self._update_connection_ui, True)
                self.root.after(0, lambda: self._add_activity_log(f"✅ Connected to teacher at {teacher_ip}"))
            else:
                self.root.after(0, lambda: show_error_message("Error", "Failed to connect to teacher"))
                
        except Exception as e:
            self.root.after(0, lambda: show_error_message("Error", f"Connection error: {e}"))
    
    def disconnect_from_teacher(self):
        """Disconnect from teacher"""
        if ask_yes_no("Confirm", "Disconnect from the session?"):
            def run_async_task():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._disconnect_async())
                except Exception as e:
                    self.logger.error(f"Error in disconnection task: {e}")
                finally:
                    loop.close()
            
            threading.Thread(target=run_async_task, daemon=True).start()
    
    async def _disconnect_async(self):
        """Async disconnection"""
        try:
            await self.network_manager.disconnect_client()
            if self.focus_mode_active:
                await self.focus_manager.disable_focus_mode()
                self.focus_mode_active = False
            
            self.connected = False
            self.root.after(0, self._update_connection_ui, False)
            self.root.after(0, lambda: self._add_activity_log("❌ Disconnected from teacher"))
            
        except Exception as e:
            self.logger.error(f"Disconnection error: {e}")
    
    def _update_connection_ui(self, connected: bool):
        """Update UI based on connection status"""
        if connected:
            self.connection_status_var.set("Connected")
            self.connect_btn.configure(state=tk.DISABLED)
            self.disconnect_btn.configure(state=tk.NORMAL)
            self.status_var.set("Connected to teacher")
            
            for widget in [self.name_entry, self.teacher_ip_entry, self.session_code_entry, self.password_entry]:
                widget.configure(state=tk.DISABLED)
        else:
            self.connection_status_var.set("Disconnected")
            self.connect_btn.configure(state=tk.NORMAL)
            self.disconnect_btn.configure(state=tk.DISABLED)
            self.status_var.set("Not connected")
            self.focus_mode_var.set("Disabled")
            
            for widget in [self.name_entry, self.teacher_ip_entry, self.session_code_entry, self.password_entry]:
                widget.configure(state=tk.NORMAL)
    
    async def handle_auth_success(self, client_id: str, data: dict):
        """Handle successful authentication"""
        self.root.after(0, lambda: self._add_activity_log("✅ Authentication successful"))
    
    async def handle_enable_focus_mode(self, client_id: str, data: dict):
        """Handle focus mode enable request"""
        try:
            allowed_windows = data.get("allowed_windows", ["FocusClass Student"])
            success = await self.focus_manager.enable_focus_mode(allowed_windows)
            
            if success:
                self.focus_mode_active = True
                self.root.after(0, lambda: self.focus_mode_var.set("Enabled"))
                self.root.after(0, lambda: self._add_activity_log("🔒 Focus mode enabled"))
            else:
                self.root.after(0, lambda: self._add_activity_log("❌ Failed to enable focus mode"))
                
        except Exception as e:
            self.logger.error(f"Error enabling focus mode: {e}")
    
    async def handle_disable_focus_mode(self, client_id: str, data: dict):
        """Handle focus mode disable request"""
        try:
            await self.focus_manager.disable_focus_mode()
            self.focus_mode_active = False
            self.root.after(0, lambda: self.focus_mode_var.set("Disabled"))
            self.root.after(0, lambda: self._add_activity_log("🔓 Focus mode disabled"))
            
        except Exception as e:
            self.logger.error(f"Error disabling focus mode: {e}")
    
    async def handle_focus_violation(self, violation_data: dict):
        """Handle focus mode violation"""
        try:
            violation_type = violation_data.get("type", "unknown")
            description = violation_data.get("description", "")
            
            await self._send_violation(violation_type, description)
            
            self.violation_count += 1
            self.root.after(0, lambda: self.violation_count_var.set(str(self.violation_count)))
            self.root.after(0, lambda: self._add_activity_log(f"⚠️ Violation: {violation_type}"))
            
        except Exception as e:
            self.logger.error(f"Error handling violation: {e}")
    
    async def handle_screen_share_request(self, request_data: dict):
        """Handle screen share request from teacher"""
        try:
            approved = ask_yes_no("Screen Share Request", "Teacher is requesting to view your screen. Allow?")
            
            if approved:
                success = await self.screen_share.handle_share_request(request_data)
                if success.get("success"):
                    self.root.after(0, lambda: self._add_activity_log("📺 Screen sharing started"))
                else:
                    self.root.after(0, lambda: self._add_activity_log("❌ Failed to start screen sharing"))
            else:
                self.root.after(0, lambda: self._add_activity_log("❌ Screen sharing request denied"))
                
        except Exception as e:
            self.logger.error(f"Error handling screen share request: {e}")
    
    async def _send_violation(self, violation_type: str, description: str):
        """Send violation to teacher"""
        try:
            if self.connected:
                await self.network_manager._send_message("teacher", "violation", {
                    "type": violation_type,
                    "description": description,
                    "timestamp": time.time(),
                    "student_name": self.student_name
                })
        except Exception as e:
            self.logger.error(f"Error sending violation: {e}")
    
    async def handle_disconnection(self, client_id: str):
        """Handle disconnection from teacher"""
        self.connected = False
        if self.focus_mode_active:
            await self.focus_manager.disable_focus_mode()
            self.focus_mode_active = False
        
        self.root.after(0, self._update_connection_ui, False)
        self.root.after(0, lambda: self._add_activity_log("❌ Connection lost to teacher"))
    
    def _add_activity_log(self, message: str):
        """Add activity log message"""
        timestamp = time.strftime("%H:%M:%S")
        self.activity_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.activity_text.see(tk.END)
        
        # Keep only last 100 lines
        lines = self.activity_text.get(1.0, tk.END).splitlines()
        if len(lines) > 100:
            self.activity_text.delete(1.0, f"{len(lines) - 100}.0")
    
    def run(self):
        """Run the application"""
        try:
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in student app main loop: {e}")
        finally:
            # Clean shutdown
            try:
                if self.connected:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._disconnect_async())
                    loop.close()
            except Exception as cleanup_error:
                self.logger.error(f"Error during cleanup: {cleanup_error}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = StudentApp(root)
    app.run()


if __name__ == "__main__":
    main()