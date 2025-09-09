"""
Teacher Application for FocusClass Tkinter - Main File
"""

import sys
import asyncio
import logging
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
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
        
        # Initialize async helper first
        self.async_helper = AsyncTkinterHelper(root)
        self.async_tasks = set()  # Track async tasks for cleanup
        
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
        
        # UI Variables - initialize early
        self.session_code_var = tk.StringVar(value="Not Started")
        self.session_password_var = tk.StringVar(value="")
        self.password_display_var = tk.StringVar(value="")
        self.teacher_ip_var = tk.StringVar(value=get_local_ip())
        self.password_hidden = True
        
        # Header variables
        self.header_status_var = tk.StringVar(value="Ready to start session")
        self.duration_header_var = tk.StringVar(value="00:00:00")
        self.students_header_var = tk.StringVar(value="0")
        self.violations_header_var = tk.StringVar(value="0")
        
        # Status variables
        self.status_var = tk.StringVar(value="Ready")
        self.network_status_var = tk.StringVar(value="Network: Ready")
        self.ports_status_var = tk.StringVar(value="Ports: Not started")
        
        # Statistics variables
        self.duration_var = tk.StringVar(value="00:00:00")
        self.students_count_var = tk.StringVar(value="0")
        self.violations_count_var = tk.StringVar(value="0")
        self.students_count_display_var = tk.StringVar(value="Students Connected: 0")
        
        # Activity log variables
        self.activity_filter_var = tk.StringVar(value="All")
        self.auto_scroll_var = tk.BooleanVar(value=True)
        self.total_activities_var = tk.StringVar(value="Total Activities: 0")
        
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
        self.root.title("FocusClass Teacher Dashboard")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)
        self.root.configure(bg=TKINTER_THEME["bg_color"])
        
        # Configure root grid for responsiveness
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create main layout with responsive design
        self.create_enhanced_main_layout()
        center_window(self.root, 1400, 900)
    
    def create_enhanced_main_layout(self):
        """Create enhanced main layout with more features"""
        # Main container with improved styling
        main_frame = tk.Frame(self.root, bg=TKINTER_THEME["bg_color"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header section with logo and session info
        header_frame = tk.Frame(main_frame, bg=TKINTER_THEME["bg_color"], height=80)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        header_frame.pack_propagate(False)
        
        # Title and status
        title_frame = tk.Frame(header_frame, bg=TKINTER_THEME["bg_color"])
        title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(title_frame, text="📚 FocusClass Teacher Dashboard", 
                bg=TKINTER_THEME["bg_color"], fg=TKINTER_THEME["accent_color"],
                font=(TKINTER_THEME["font_family"], 20, "bold")).pack(anchor="w")
        
        self.header_status_var = tk.StringVar(value="Ready to start session")
        tk.Label(title_frame, textvariable=self.header_status_var,
                bg=TKINTER_THEME["bg_color"], fg=TKINTER_THEME["fg_color"],
                font=(TKINTER_THEME["font_family"], 12)).pack(anchor="w")
        
        # Session stats in header
        stats_header_frame = tk.Frame(header_frame, bg=TKINTER_THEME["bg_color"])
        stats_header_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        
        # Quick stats display
        quick_stats_frame = tk.Frame(stats_header_frame, bg="white", relief=tk.RAISED, bd=1)
        quick_stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Stats grid
        tk.Label(quick_stats_frame, text="Session Duration:", bg="white", font=("Arial", 9)).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.duration_header_var = tk.StringVar(value="00:00:00")
        tk.Label(quick_stats_frame, textvariable=self.duration_header_var, bg="white", font=("Arial", 9, "bold")).grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(quick_stats_frame, text="Students:", bg="white", font=("Arial", 9)).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.students_header_var = tk.StringVar(value="0")
        tk.Label(quick_stats_frame, textvariable=self.students_header_var, bg="white", font=("Arial", 9, "bold")).grid(row=1, column=1, sticky="w", padx=5)
        
        tk.Label(quick_stats_frame, text="Violations:", bg="white", font=("Arial", 9)).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.violations_header_var = tk.StringVar(value="0")
        tk.Label(quick_stats_frame, textvariable=self.violations_header_var, bg="white", font=("Arial", 9, "bold")).grid(row=2, column=1, sticky="w", padx=5)
        
        # Main content area with three columns
        content_frame = tk.Frame(main_frame, bg=TKINTER_THEME["bg_color"])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Session controls (30%)
        left_frame = tk.Frame(content_frame, bg=TKINTER_THEME["bg_color"], width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_frame.pack_propagate(False)
        
        # Center panel - Students and monitoring (40%)
        center_frame = tk.Frame(content_frame, bg=TKINTER_THEME["bg_color"])
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Right panel - Activities and logs (30%)
        right_frame = tk.Frame(content_frame, bg=TKINTER_THEME["bg_color"], width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)
        
        # Build panels
        self.create_session_control_panel(left_frame)
        self.create_monitoring_panel(center_frame)
        self.create_activity_panel(right_frame)
        
        # Enhanced status bar
        self.create_enhanced_status_bar()
    
    def create_session_control_panel(self, parent):
        """Create enhanced session control panel"""
        # Session information group with enhanced styling
        session_group = tk.LabelFrame(parent, text="📋 Session Information", 
                                     bg=TKINTER_THEME["bg_color"], 
                                     font=(TKINTER_THEME["font_family"], 12, "bold"),
                                     relief=tk.RAISED, bd=2)
        session_group.pack(fill=tk.X, pady=(0, 10))
        
        # Session details with improved layout
        info_frame = tk.Frame(session_group, bg=TKINTER_THEME["bg_color"])
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Session code with copy button
        code_frame = tk.Frame(info_frame, bg=TKINTER_THEME["bg_color"])
        code_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(code_frame, text="Session Code:", bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.session_code_var = tk.StringVar(value="Not Started")
        code_label = tk.Label(code_frame, textvariable=self.session_code_var, 
                             bg="white", fg="black", relief=tk.SUNKEN, bd=1,
                             font=("Courier", 12, "bold"), padx=5)
        code_label.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        
        copy_btn = tk.Button(code_frame, text="📋", command=self.copy_session_code,
                            bg=TKINTER_THEME["accent_color"], fg="white", width=3)
        copy_btn.pack(side=tk.RIGHT)
        
        # Copy all details button
        copy_all_btn = tk.Button(code_frame, text="📄", command=self.copy_all_session_details,
                                bg=TKINTER_THEME["success_color"], fg="white", width=3)
        copy_all_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Password with show/hide
        pass_frame = tk.Frame(info_frame, bg=TKINTER_THEME["bg_color"])
        pass_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(pass_frame, text="Password:", bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.session_password_var = tk.StringVar(value="")
        self.password_display_var = tk.StringVar(value="")
        self.password_hidden = True
        
        pass_label = tk.Label(pass_frame, textvariable=self.password_display_var, 
                             bg="white", fg="black", relief=tk.SUNKEN, bd=1,
                             font=("Courier", 12), padx=5)
        pass_label.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        
        self.show_pass_btn = tk.Button(pass_frame, text="👁", command=self.toggle_password_visibility,
                                      bg=TKINTER_THEME["warning_color"], fg="white", width=3)
        self.show_pass_btn.pack(side=tk.RIGHT)
        
        # IP and ports
        tk.Label(info_frame, text="Teacher IP:", bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 10, "bold")).pack(anchor="w", pady=(5, 0))
        
        self.teacher_ip_var = tk.StringVar(value=get_local_ip())
        tk.Label(info_frame, textvariable=self.teacher_ip_var, 
                bg="white", relief=tk.SUNKEN, bd=1, padx=5,
                font=("Courier", 11)).pack(fill=tk.X, pady=(2, 5))
        
        # QR Code with improved styling
        qr_frame = tk.Frame(session_group, bg=TKINTER_THEME["bg_color"], relief=tk.SUNKEN, bd=2)
        qr_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(qr_frame, text="QR Code for Quick Connect", 
                bg=TKINTER_THEME["bg_color"], font=("Arial", 10, "bold")).pack(pady=5)
        
        self.qr_label = tk.Label(qr_frame, bg="white", text="Start session to generate QR code",
                                font=("Arial", 9), width=25, height=8, relief=tk.SUNKEN, bd=1)
        self.qr_label.pack(pady=5)
        
        # Enhanced control buttons
        controls_group = tk.LabelFrame(parent, text="🎮 Session Controls", 
                                      bg=TKINTER_THEME["bg_color"],
                                      font=(TKINTER_THEME["font_family"], 12, "bold"),
                                      relief=tk.RAISED, bd=2)
        controls_group.pack(fill=tk.X, pady=(0, 10))
        
        btn_frame = tk.Frame(controls_group, bg=TKINTER_THEME["bg_color"])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Start session button
        self.start_btn = tk.Button(btn_frame, text="🚀 Start New Session", 
                                  command=self.start_session,
                                  bg=TKINTER_THEME["success_color"], fg="white",
                                  font=("Arial", 11, "bold"), height=2,
                                  relief=tk.RAISED, bd=3)
        self.start_btn.pack(fill=tk.X, pady=2)
        
        # Screen sharing button
        self.screen_btn = tk.Button(btn_frame, text="📺 Start Screen Sharing", 
                                   command=self.start_screen_sharing,
                                   bg=TKINTER_THEME["accent_color"], fg="white",
                                   font=("Arial", 10), state=tk.DISABLED,
                                   relief=tk.RAISED, bd=2)
        self.screen_btn.pack(fill=tk.X, pady=2)
        
        # Focus mode button
        self.focus_btn = tk.Button(btn_frame, text="🔒 Enable Focus Mode", 
                                  command=self.enable_focus_mode,
                                  bg=TKINTER_THEME["warning_color"], fg="white",
                                  font=("Arial", 10), state=tk.DISABLED,
                                  relief=tk.RAISED, bd=2)
        self.focus_btn.pack(fill=tk.X, pady=2)
        
        # End session button
        self.end_btn = tk.Button(btn_frame, text="🛑 End Session", 
                                command=self.end_session,
                                bg=TKINTER_THEME["error_color"], fg="white",
                                font=("Arial", 10), state=tk.DISABLED,
                                relief=tk.RAISED, bd=2)
        self.end_btn.pack(fill=tk.X, pady=2)
        
        # Additional controls
        extra_controls = tk.LabelFrame(parent, text="🔧 Additional Tools", 
                                      bg=TKINTER_THEME["bg_color"],
                                      font=(TKINTER_THEME["font_family"], 10, "bold"))
        extra_controls.pack(fill=tk.X, pady=(0, 10))
        
        extra_btn_frame = tk.Frame(extra_controls, bg=TKINTER_THEME["bg_color"])
        extra_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Export button
        export_btn = tk.Button(extra_btn_frame, text="📊 Export Data", 
                              command=self.export_session_data,
                              bg=TKINTER_THEME["bg_color"], 
                              relief=tk.RAISED, bd=1)
        export_btn.pack(fill=tk.X, pady=1)
        
        # Clear logs button
        clear_btn = tk.Button(extra_btn_frame, text="🗑️ Clear Logs", 
                             command=self.clear_activity_log,
                             bg=TKINTER_THEME["bg_color"], 
                             relief=tk.RAISED, bd=1)
        clear_btn.pack(fill=tk.X, pady=1)
    
    def create_monitoring_panel(self, parent):
        """Create enhanced monitoring panel"""
        # Students monitoring with enhanced features
        students_group = tk.LabelFrame(parent, text="👥 Connected Students", 
                                      bg=TKINTER_THEME["bg_color"],
                                      font=(TKINTER_THEME["font_family"], 12, "bold"),
                                      relief=tk.RAISED, bd=2)
        students_group.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Students header with count
        students_header = tk.Frame(students_group, bg=TKINTER_THEME["bg_color"])
        students_header.pack(fill=tk.X, padx=10, pady=5)
        
        self.students_count_display_var = tk.StringVar(value="Students Connected: 0")
        tk.Label(students_header, textvariable=self.students_count_display_var,
                bg=TKINTER_THEME["bg_color"], font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        
        # Refresh button
        refresh_btn = tk.Button(students_header, text="🔄", command=self.refresh_students,
                               bg=TKINTER_THEME["accent_color"], fg="white", width=3)
        refresh_btn.pack(side=tk.RIGHT)
        
        # Students list with scrollbar and enhanced display
        students_frame = tk.Frame(students_group, bg=TKINTER_THEME["bg_color"])
        students_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Create Treeview for better student display
        columns = ('name', 'ip', 'status', 'violations')
        self.students_tree = ttk.Treeview(students_frame, columns=columns, show='headings', height=8)
        
        # Configure columns
        self.students_tree.heading('name', text='Student Name')
        self.students_tree.heading('ip', text='IP Address')
        self.students_tree.heading('status', text='Status')
        self.students_tree.heading('violations', text='Violations')
        
        self.students_tree.column('name', width=120)
        self.students_tree.column('ip', width=100)
        self.students_tree.column('status', width=80)
        self.students_tree.column('violations', width=80)
        
        # Scrollbars for treeview
        v_scrollbar = ttk.Scrollbar(students_frame, orient=tk.VERTICAL, command=self.students_tree.yview)
        h_scrollbar = ttk.Scrollbar(students_frame, orient=tk.HORIZONTAL, command=self.students_tree.xview)
        self.students_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid the treeview and scrollbars
        self.students_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        students_frame.grid_rowconfigure(0, weight=1)
        students_frame.grid_columnconfigure(0, weight=1)
        
        # Student actions
        student_actions = tk.Frame(students_group, bg=TKINTER_THEME["bg_color"])
        student_actions.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        kick_btn = tk.Button(student_actions, text="⚠️ Kick Selected", 
                            command=self.kick_selected_student,
                            bg=TKINTER_THEME["error_color"], fg="white",
                            font=("Arial", 9))
        kick_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        message_btn = tk.Button(student_actions, text="💬 Send Message", 
                               command=self.send_message_to_selected,
                               bg=TKINTER_THEME["accent_color"], fg="white",
                               font=("Arial", 9))
        message_btn.pack(side=tk.LEFT)
        
        # Statistics panel
        stats_group = tk.LabelFrame(parent, text="📊 Session Statistics", 
                                   bg=TKINTER_THEME["bg_color"],
                                   font=(TKINTER_THEME["font_family"], 12, "bold"),
                                   relief=tk.RAISED, bd=2)
        stats_group.pack(fill=tk.X)
        
        stats_grid = tk.Frame(stats_group, bg=TKINTER_THEME["bg_color"])
        stats_grid.pack(fill=tk.X, padx=15, pady=10)
        
        # Configure grid for stats
        for i in range(3):
            stats_grid.grid_columnconfigure(i, weight=1)
        
        # Duration
        duration_frame = tk.Frame(stats_grid, bg="white", relief=tk.RAISED, bd=2)
        duration_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        tk.Label(duration_frame, text="🕐 Duration", bg="white", 
                font=("Arial", 10, "bold")).pack(pady=2)
        self.duration_var = tk.StringVar(value="00:00:00")
        tk.Label(duration_frame, textvariable=self.duration_var, bg="white", 
                font=("Arial", 14, "bold"), fg=TKINTER_THEME["accent_color"]).pack(pady=2)
        
        # Students count
        students_frame_stat = tk.Frame(stats_grid, bg="white", relief=tk.RAISED, bd=2)
        students_frame_stat.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        tk.Label(students_frame_stat, text="👥 Students", bg="white", 
                font=("Arial", 10, "bold")).pack(pady=2)
        self.students_count_var = tk.StringVar(value="0")
        tk.Label(students_frame_stat, textvariable=self.students_count_var, bg="white", 
                font=("Arial", 14, "bold"), fg=TKINTER_THEME["success_color"]).pack(pady=2)
        
        # Violations count
        violations_frame = tk.Frame(stats_grid, bg="white", relief=tk.RAISED, bd=2)
        violations_frame.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        tk.Label(violations_frame, text="⚠️ Violations", bg="white", 
                font=("Arial", 10, "bold")).pack(pady=2)
        self.violations_count_var = tk.StringVar(value="0")
        tk.Label(violations_frame, textvariable=self.violations_count_var, bg="white", 
                font=("Arial", 14, "bold"), fg=TKINTER_THEME["error_color"]).pack(pady=2)
    
    def create_activity_panel(self, parent):
        """Create enhanced activity and logs panel"""
        # Activity log with filters
        activity_group = tk.LabelFrame(parent, text="📋 Activity Log", 
                                      bg=TKINTER_THEME["bg_color"],
                                      font=(TKINTER_THEME["font_family"], 12, "bold"),
                                      relief=tk.RAISED, bd=2)
        activity_group.pack(fill=tk.BOTH, expand=True)
        
        # Activity controls
        activity_controls = tk.Frame(activity_group, bg=TKINTER_THEME["bg_color"])
        activity_controls.pack(fill=tk.X, padx=10, pady=5)
        
        # Filter options
        tk.Label(activity_controls, text="Filter:", bg=TKINTER_THEME["bg_color"], 
                font=("Arial", 9)).pack(side=tk.LEFT)
        
        self.activity_filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(activity_controls, textvariable=self.activity_filter_var,
                                   values=["All", "Connections", "Violations", "Errors", "Info"],
                                   width=10, state="readonly")
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", self.filter_activity_log)
        
        # Auto-scroll toggle
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_cb = tk.Checkbutton(activity_controls, text="Auto-scroll", 
                                       variable=self.auto_scroll_var,
                                       bg=TKINTER_THEME["bg_color"],
                                       font=("Arial", 8))
        auto_scroll_cb.pack(side=tk.RIGHT)
        
        # Activity text with enhanced styling
        self.activities_text = scrolledtext.ScrolledText(activity_group, 
                                                        height=20, 
                                                        bg="black", 
                                                        fg="lime",
                                                        font=("Consolas", 9),
                                                        insertbackground="lime",
                                                        relief=tk.SUNKEN, bd=2)
        self.activities_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Configure text tags for colored output
        self.activities_text.tag_configure("info", foreground="lime")
        self.activities_text.tag_configure("warning", foreground="yellow")
        self.activities_text.tag_configure("error", foreground="red")
        self.activities_text.tag_configure("success", foreground="lightgreen")
        self.activities_text.tag_configure("violation", foreground="orange")
        
        # Activity statistics
        activity_stats = tk.Frame(activity_group, bg=TKINTER_THEME["bg_color"])
        activity_stats.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.total_activities_var = tk.StringVar(value="Total Activities: 0")
        tk.Label(activity_stats, textvariable=self.total_activities_var,
                bg=TKINTER_THEME["bg_color"], font=("Arial", 8)).pack(side=tk.LEFT)
        
    def create_enhanced_status_bar(self):
        """Create enhanced status bar with more information"""
        status_frame = tk.Frame(self.root, bg=TKINTER_THEME["bg_color"], relief=tk.SUNKEN, bd=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Main status
        self.status_var = tk.StringVar(value="Ready - Start a session to begin")
        status_main = tk.Label(status_frame, textvariable=self.status_var, 
                              bg=TKINTER_THEME["bg_color"], anchor=tk.W,
                              font=("Arial", 9))
        status_main.pack(side=tk.LEFT, padx=5)
        
        # Network status
        self.network_status_var = tk.StringVar(value="Network: Ready")
        network_status = tk.Label(status_frame, textvariable=self.network_status_var,
                                 bg=TKINTER_THEME["bg_color"], 
                                 font=("Arial", 9))
        network_status.pack(side=tk.RIGHT, padx=5)
        
        # Server ports
        self.ports_status_var = tk.StringVar(value="Ports: Not started")
        ports_status = tk.Label(status_frame, textvariable=self.ports_status_var,
                               bg=TKINTER_THEME["bg_color"], 
                               font=("Arial", 9))
        ports_status.pack(side=tk.RIGHT, padx=5)
    
    def copy_session_code(self):
        """Copy session code to clipboard"""
        try:
            session_code = self.session_code_var.get()
            if session_code and session_code != "Not Started":
                self.root.clipboard_clear()
                self.root.clipboard_append(session_code)
                self.root.update()  # Required for clipboard to work
                show_info_message("Copied", f"Session code '{session_code}' copied to clipboard!")
            else:
                show_error_message("Error", "No active session code to copy")
        except Exception as e:
            self.logger.error(f"Error copying session code: {e}")
    
    def copy_all_session_details(self):
        """Copy all session details to clipboard"""
        try:
            session_code = self.session_code_var.get()
            password = self.session_password_var.get()
            teacher_ip = self.teacher_ip_var.get()
            
            if session_code and session_code != "Not Started":
                # Get current port information
                ws_port = getattr(self.network_manager, 'websocket_port', 8765)
                http_port = getattr(self.network_manager, 'http_port', 8080)
                
                details = f"""FocusClass Session Details
=============================
Session Code: {session_code}
Password: {password}
Teacher IP: {teacher_ip}
WebSocket Port: {ws_port}
HTTP Port: {http_port}

Instructions for Students:
1. Open FocusClass Student Application
2. Enter your name
3. Enter Teacher IP: {teacher_ip}
4. Enter Session Code: {session_code}
5. Enter Password: {password}
6. Click Connect

Alternatively, scan the QR code from the teacher dashboard."""
                
                self.root.clipboard_clear()
                self.root.clipboard_append(details)
                self.root.update()  # Required for clipboard to work
                
                show_info_message("Copied", "All session details copied to clipboard!\nYou can now share this with students.")
                self._add_activity_log("Session details copied to clipboard", "info")
            else:
                show_error_message("Error", "No active session to copy")
        except Exception as e:
            self.logger.error(f"Error copying session details: {e}")
            show_error_message("Error", f"Failed to copy session details: {e}")
    
    def toggle_password_visibility(self):
        """Toggle password visibility"""
        try:
            if self.password_hidden:
                self.password_display_var.set(self.session_password_var.get())
                self.show_pass_btn.configure(text="🙈")
                self.password_hidden = False
            else:
                password = self.session_password_var.get()
                self.password_display_var.set("*" * len(password) if password else "")
                self.show_pass_btn.configure(text="👁")
                self.password_hidden = True
        except Exception as e:
            self.logger.error(f"Error toggling password visibility: {e}")
    
    def refresh_students(self):
        """Refresh students list"""
        self._update_students_tree()
        self._add_activity_log("🔄 Students list refreshed", "info")
    
    def kick_selected_student(self):
        """Kick selected student from session"""
        try:
            selection = self.students_tree.selection()
            if not selection:
                show_error_message("Error", "Please select a student to kick")
                return
            
            item = self.students_tree.item(selection[0])
            student_name = item['values'][0]
            
            if ask_yes_no("Confirm", f"Kick student '{student_name}' from the session?"):
                # Find student by name and disconnect
                for client_id, student_info in self.connected_students.items():
                    if student_info['name'] == student_name:
                        def run_async_task():
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(self.network_manager._send_message(client_id, "kicked", {
                                    "reason": "Removed by teacher"
                                }))
                            finally:
                                loop.close()
                        
                        threading.Thread(target=run_async_task, daemon=True).start()
                        self._add_activity_log(f"⚠️ Kicked student: {student_name}", "warning")
                        break
        except Exception as e:
            self.logger.error(f"Error kicking student: {e}")
            show_error_message("Error", f"Failed to kick student: {e}")
    
    def send_message_to_selected(self):
        """Send message to selected student"""
        try:
            selection = self.students_tree.selection()
            if not selection:
                show_error_message("Error", "Please select a student to message")
                return
            
            item = self.students_tree.item(selection[0])
            student_name = item['values'][0]
            
            # Create message dialog
            message = tk.simpledialog.askstring("Send Message", 
                                               f"Message to {student_name}:",
                                               parent=self.root)
            
            if message:
                # Find student and send message
                for client_id, student_info in self.connected_students.items():
                    if student_info['name'] == student_name:
                        def run_async_task():
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(self.network_manager._send_message(client_id, "teacher_message", {
                                    "message": message,
                                    "timestamp": time.time()
                                }))
                            finally:
                                loop.close()
                        
                        threading.Thread(target=run_async_task, daemon=True).start()
                        self._add_activity_log(f"💬 Sent message to {student_name}: {message}", "info")
                        break
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
    
    def filter_activity_log(self, event=None):
        """Filter activity log based on selected filter"""
        try:
            filter_type = self.activity_filter_var.get().lower()
            # This is a placeholder - in a full implementation, you'd store
            # log entries with types and filter them
            self._add_activity_log(f"🔍 Filter applied: {filter_type}", "info")
        except Exception as e:
            self.logger.error(f"Error filtering activity log: {e}")
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
                duration_str = format_duration(duration)
                self.duration_var.set(duration_str)
                self.duration_header_var.set(duration_str)
                
                # Update student count
                student_count = len(self.connected_students)
                self.students_count_var.set(str(student_count))
                self.students_header_var.set(str(student_count))
                self.students_count_display_var.set(f"Students Connected: {student_count}")
                
                # Update violations count
                total_violations = sum(student.get('violations', 0) for student in self.connected_students.values())
                self.violations_count_var.set(str(total_violations))
                self.violations_header_var.set(str(total_violations))
                
                # Update header status
                self.header_status_var.set(f"Session Active - {student_count} students connected")
            
            # Schedule next update
            self.root.after(1000, update)
        
        update()
    
    def start_session(self):
        """Start a new session"""
        def run_async_task():
            error_message = None
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._start_session_async())
            except Exception as e:
                error_message = str(e)
                self.logger.error(f"Error in async task: {e}")
            finally:
                loop.close()
                # Show error on main thread if there was one
                if error_message:
                    self.root.after(0, lambda msg=error_message: show_error_message("Error", f"Failed to start session: {msg}"))
        
        # Use thread for async task to avoid blocking UI
        threading.Thread(target=run_async_task, daemon=True).start()
    
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
            
            # Update UI on main thread
            self.root.after(0, self._update_session_ui, session_code, password, teacher_ip, server_info)
            self.logger.info(f"Session started: {session_code}")
            
        except Exception as e:
            self.logger.error(f"Failed to start session: {e}")
            self.root.after(0, lambda: show_error_message("Error", f"Failed to start session: {e}"))
    
    def _update_session_ui(self, session_code: str, password: str, teacher_ip: str, server_info: dict = None):
        """Update UI with session information (must run on main thread)"""
        try:
            self.session_code_var.set(session_code)
            self.session_password_var.set(password)
            
            # Update password display based on visibility setting
            if self.password_hidden:
                self.password_display_var.set("*" * len(password))
            else:
                self.password_display_var.set(password)
            
            self.teacher_ip_var.set(teacher_ip)
            
            # Generate QR code on main thread with proper error handling
            self.root.after(200, lambda: self._safe_generate_qr_code(teacher_ip, session_code, password))
            
            # Update buttons
            self.start_btn.configure(state=tk.DISABLED, text="✅ Session Active")
            self.screen_btn.configure(state=tk.NORMAL)
            self.focus_btn.configure(state=tk.NORMAL)
            self.end_btn.configure(state=tk.NORMAL)
            
            # Update status
            self.status_var.set(f"Session Active: {session_code}")
            self.header_status_var.set("Session started successfully")
            self.network_status_var.set("Network: Connected")
            
            # Get server info and update ports status
            if server_info:
                ws_port = server_info.get('websocket_port', 8765)
                http_port = server_info.get('http_port', 8080)
                self.ports_status_var.set(f"Ports: WS:{ws_port}, HTTP:{http_port}")
            
            # Add success log
            self._add_activity_log(f"Session {session_code} started successfully on {teacher_ip}", "success")
            
        except Exception as e:
            self.logger.error(f"Error updating session UI: {e}")
            show_error_message("UI Error", f"Failed to update interface: {e}")
    
    def _safe_generate_qr_code(self, teacher_ip: str, session_code: str, password: str):
        """Safely generate QR code with better error handling"""
        try:
            # Check if QR label still exists and is valid
            if not hasattr(self, 'qr_label'):
                self.logger.warning("QR label not found, skipping QR generation")
                return
            
            try:
                # Test if the widget still exists
                self.qr_label.winfo_exists()
            except tk.TclError:
                self.logger.warning("QR label widget no longer exists")
                return
            
            # Generate QR code
            try:
                qr_data = {
                    "type": "focusclass_session", 
                    "teacher_ip": teacher_ip, 
                    "session_code": session_code, 
                    "password": password
                }
                
                qr_image = create_qr_code(qr_data, size=150)
                
                # Create PhotoImage in a try-catch
                try:
                    qr_photo = ImageTk.PhotoImage(qr_image)
                    self.qr_label.configure(image=qr_photo, text="")
                    self.qr_label.image = qr_photo  # Keep reference
                    self.logger.info("QR code generated successfully")
                except Exception as photo_error:
                    self.logger.error(f"Error creating PhotoImage: {photo_error}")
                    raise photo_error
                    
            except Exception as qr_error:
                self.logger.error(f"Error generating QR code: {qr_error}")
                self._set_qr_fallback_text(session_code, teacher_ip, password)
                
        except Exception as e:
            self.logger.error(f"Error in safe QR generation: {e}")
            # Set fallback text as last resort
            try:
                self._set_qr_fallback_text(session_code, teacher_ip, password)
            except:
                pass  # Complete failure, give up
    
    def _generate_qr_code(self, teacher_ip: str, session_code: str, password: str):
        """Generate QR code safely on main thread"""
        try:
            # Ensure we're on the main thread and QR label exists
            if not hasattr(self, 'qr_label') or not self.qr_label.winfo_exists():
                self.logger.warning("QR label not ready, skipping QR generation")
                return
            
            # Create QR code data
            qr_data = {
                "type": "focusclass_session", 
                "teacher_ip": teacher_ip, 
                "session_code": session_code, 
                "password": password
            }
            
            # Generate QR code image
            qr_image = create_qr_code(qr_data, size=150)
            
            # Convert to PhotoImage on main thread
            qr_photo = ImageTk.PhotoImage(qr_image)
            
            # Update label safely
            try:
                self.qr_label.configure(image=qr_photo, text="")
                self.qr_label.image = qr_photo  # Keep reference to prevent garbage collection
                self.logger.info("QR code generated successfully")
            except (tk.TclError, AttributeError) as e:
                self.logger.error(f"Tkinter error updating QR label: {e}")
                self._set_qr_fallback_text(session_code, teacher_ip, password)
            
        except Exception as e:
            self.logger.error(f"Failed to generate QR code: {e}")
            self._set_qr_fallback_text(session_code, teacher_ip, password)
    
    def _set_qr_fallback_text(self, session_code: str, teacher_ip: str, password: str):
        """Set fallback text when QR code generation fails"""
        try:
            fallback_text = f"Session: {session_code}\nIP: {teacher_ip}\nPassword: {password[:8]}..."
            self.qr_label.configure(image="", text=fallback_text)
            # Clear any existing image reference
            if hasattr(self.qr_label, 'image'):
                delattr(self.qr_label, 'image')
        except Exception as e:
            self.logger.error(f"Error setting QR fallback text: {e}")
    
    def end_session(self):
        """End current session"""
        if ask_yes_no("Confirm", "End the session?"):
            def run_async_task():
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._end_session_async())
                except Exception as e:
                    self.logger.error(f"Error ending session: {e}")
                finally:
                    loop.close()
            
            threading.Thread(target=run_async_task, daemon=True).start()
    
    async def _end_session_async(self):
        """Async session end"""
        try:
            # Save session data first
            if self.session_id:
                await self.db_manager.end_session(self.session_id)
            
            # Stop network server with proper cleanup
            await self.network_manager.stop_server()
            
            # Stop screen sharing
            if self.screen_sharing_active:
                self.screen_capture.stop_capture()
            
            # Reset state
            self.session_active = False
            self.screen_sharing_active = False
            self.focus_mode_active = False
            
            # Update UI on main thread
            self.root.after(0, self._reset_session_ui)
            self.root.after(0, lambda: self._add_activity_log("Session ended successfully", "info"))
            
            self.logger.info("Session ended successfully")
            
        except Exception as e:
            self.logger.error(f"Error ending session: {e}")
            # Show error but still reset UI
            self.root.after(0, lambda: show_error_message("Warning", f"Session ended with errors: {e}"))
            self.root.after(0, self._reset_session_ui)
    
    def _reset_session_ui(self):
        """Reset UI to initial state"""
        self.session_code_var.set("Not Started")
        self.session_password_var.set("")
        self.password_display_var.set("")
        
        # Reset QR code
        self.qr_label.configure(image="", text="Start session to generate QR code")
        if hasattr(self.qr_label, 'image'):
            delattr(self.qr_label, 'image')  # Remove image reference
        
        # Reset buttons
        self.start_btn.configure(state=tk.NORMAL, text="🚀 Start New Session")
        self.screen_btn.configure(state=tk.DISABLED, text="📺 Start Screen Sharing")
        self.focus_btn.configure(state=tk.DISABLED, text="🔒 Enable Focus Mode")
        self.end_btn.configure(state=tk.DISABLED)
        
        # Clear students tree
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        
        # Clear activity log
        self.activities_text.delete(1.0, tk.END)
        
        # Reset status
        self.status_var.set("Ready - Start a session to begin")
        self.header_status_var.set("Ready to start session")
        self.network_status_var.set("Network: Ready")
        self.ports_status_var.set("Ports: Not started")
        
        # Reset counters
        self.duration_var.set("00:00:00")
        self.duration_header_var.set("00:00:00")
        self.students_count_var.set("0")
        self.students_header_var.set("0")
        self.violations_count_var.set("0")
        self.violations_header_var.set("0")
        self.students_count_display_var.set("Students Connected: 0")
        self.total_activities_var.set("Total Activities: 0")
    
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
        def run_async_task():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._enable_focus_mode_async())
            except Exception as e:
                self.logger.error(f"Error enabling focus mode: {e}")
            finally:
                loop.close()
        
        threading.Thread(target=run_async_task, daemon=True).start()
    
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
        def run_async_task():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._disable_focus_mode_async())
            except Exception as e:
                self.logger.error(f"Error disabling focus mode: {e}")
            finally:
                loop.close()
        
        threading.Thread(target=run_async_task, daemon=True).start()
    
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
                self.connected_students[client_id] = {
                    "student_id": student_id, 
                    "name": student_name, 
                    "ip": student_ip,
                    "violations": 0,
                    "connected_at": time.time()
                }
            
            self.root.after(0, self._update_students_tree)
            self.root.after(0, lambda: self._add_activity_log(f"Student {student_name} ({student_ip}) connected", "success"))
            
        except Exception as e:
            self.logger.error(f"Error handling authentication: {e}")
    
    async def handle_student_disconnection(self, client_id: str):
        """Handle student disconnection"""
        try:
            if client_id in self.connected_students:
                student_info = self.connected_students[client_id]
                await self.db_manager.remove_student(student_info["student_id"])
                
                self.root.after(0, lambda: self._add_activity_log(f"Student {student_info['name']} disconnected", "warning"))
                del self.connected_students[client_id]
                self.root.after(0, self._update_students_tree)
                
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
            
            # Update student violation count
            if client_id in self.connected_students:
                self.connected_students[client_id]['violations'] = self.connected_students[client_id].get('violations', 0) + 1
            
            # Update UI
            count = self.violation_throttle[throttle_key][1]
            display_desc = description
            if count > 1:
                display_desc += f" (x{count})"
            
            self.root.after(0, lambda: self._add_activity_log(f"Violation from {student_name}: {violation_type} - {display_desc}", "violation"))
            self.root.after(0, self._update_students_tree)
            
        except Exception as e:
            self.logger.error(f"Error handling violation: {e}")
    
    def _update_students_tree(self):
        """Update students tree view"""
        # Clear existing items
        for item in self.students_tree.get_children():
            self.students_tree.delete(item)
        
        # Add current students
        for client_id, student_info in self.connected_students.items():
            name = student_info.get('name', 'Unknown')
            ip = student_info.get('ip', 'Unknown')
            violations = student_info.get('violations', 0)
            status = "Connected" if client_id in self.connected_students else "Disconnected"
            
            self.students_tree.insert('', tk.END, values=(name, ip, status, violations))
    
    def _add_activity_log(self, message: str, log_type: str = "info"):
        """Add activity log message with color coding"""
        timestamp = time.strftime("%H:%M:%S")
        
        # Determine emoji and color based on log type
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "violation": "😱"
        }
        
        emoji = emoji_map.get(log_type, "ℹ️")
        full_message = f"[{timestamp}] {emoji} {message}\n"
        
        # Insert with color tag
        self.activities_text.insert(tk.END, full_message, log_type)
        
        # Auto-scroll if enabled
        if self.auto_scroll_var.get():
            self.activities_text.see(tk.END)
        
        # Update activity count
        current_text = self.activities_text.get(1.0, tk.END)
        line_count = len(current_text.splitlines()) - 1  # -1 for empty line at end
        self.total_activities_var.set(f"Total Activities: {line_count}")
        
        # Keep only last 200 lines to prevent memory issues
        lines = current_text.splitlines()
        if len(lines) > 200:
            # Delete old lines
            self.activities_text.delete(1.0, f"{len(lines) - 200}.0")
    
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
            # Set up proper cleanup on window close
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Error in teacher app main loop: {e}")
        finally:
            # Clean shutdown
            self.cleanup()
    
    def on_closing(self):
        """Handle window closing event"""
        try:
            if self.session_active:
                if ask_yes_no("Confirm", "End the session and close the application?"):
                    # End session first
                    def run_async_task():
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(self._end_session_async())
                        finally:
                            loop.close()
                            # Close the window
                            self.root.destroy()
                    
                    threading.Thread(target=run_async_task, daemon=True).start()
                else:
                    return  # Don't close
            else:
                self.root.destroy()
        except Exception as e:
            self.logger.error(f"Error during closing: {e}")
            self.root.destroy()
    
    def cleanup(self):
        """Clean up resources"""
        try:
            # Cancel all pending async tasks
            if hasattr(self, 'async_tasks'):
                for task in self.async_tasks.copy():
                    if not task.done():
                        task.cancel()
                self.async_tasks.clear()
            
            # Stop screen sharing
            if hasattr(self, 'session_active') and self.session_active:
                self.session_active = False
                if hasattr(self, 'screen_capture') and self.screen_sharing_active:
                    self.screen_capture.stop_capture()
            
            # Clean up async helper
            if hasattr(self, 'async_helper'):
                try:
                    self.async_helper.stop_async_loop()
                except:
                    pass  # Ignore cleanup errors
            
            self.logger.info("Teacher application cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def _track_async_task(self, coro):
        """Create and track an async task"""
        task = asyncio.create_task(coro)
        self.async_tasks.add(task)
        task.add_done_callback(self.async_tasks.discard)
        return task


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