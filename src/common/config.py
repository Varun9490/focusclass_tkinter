"""
Configuration settings for FocusClass Tkinter Application
"""

import os
from pathlib import Path

# Application Information
APP_NAME = "FocusClass"
APP_VERSION = "1.0.0"
APP_AUTHOR = "FocusClass Team"

# File Paths
BASE_DIR = Path(__file__).parent.parent.parent
SRC_DIR = BASE_DIR / "src"
ASSETS_DIR = BASE_DIR / "assets"
LOGS_DIR = BASE_DIR / "logs"
EXPORTS_DIR = BASE_DIR / "exports"

# Database Configuration
DATABASE_PATH = LOGS_DIR / "focusclass.db"
DATABASE_BACKUP_INTERVAL = 3600  # seconds (1 hour)

# Network Configuration
DEFAULT_WEBSOCKET_PORT = 8765
DEFAULT_HTTP_PORT = 8080
MAX_STUDENTS = 200
CONNECTION_TIMEOUT = 30
HEARTBEAT_INTERVAL = 10

# WebRTC Configuration
STUN_SERVERS = [
    "stun:stun.l.google.com:19302",
    "stun:stun1.l.google.com:19302",
    "stun:stun2.l.google.com:19302"
]

# TURN Servers (for internet fallback)
TURN_SERVERS = [
    # Add your TURN server configuration here if needed
]

# Screen Capture Configuration
DEFAULT_FPS = 15
DEFAULT_SCALE_FACTOR = 0.75
QUALITY_PRESETS = {
    "low": {"fps": 10, "scale": 0.5},
    "medium": {"fps": 15, "scale": 0.75},
    "high": {"fps": 20, "scale": 1.0},
    "ultra": {"fps": 30, "scale": 1.0}
}

# Focus Mode Configuration
FOCUS_MODE_SETTINGS = {
    "enable_keyboard_hook": True,
    "enable_window_hook": True,
    "enable_process_monitoring": True,
    "violation_cooldown": 1.0,  # seconds
    "max_violations_per_minute": 10
}

# Security Configuration
SESSION_CODE_LENGTH = 8
PASSWORD_LENGTH = 12
MAX_LOGIN_ATTEMPTS = 3
LOGIN_COOLDOWN = 300  # seconds (5 minutes)

# UI Configuration (Tkinter-specific)
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 600
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800

# Teacher UI
TEACHER_WINDOW_TITLE = "FocusClass Teacher"
STUDENT_LIST_REFRESH_INTERVAL = 5  # seconds

# Student UI
STUDENT_WINDOW_TITLE = "FocusClass Student"
TEACHER_STREAM_RECONNECT_INTERVAL = 5  # seconds

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5

# Performance Configuration
FRAME_BUFFER_SIZE = 10
MAX_CONCURRENT_STREAMS = 50
MEMORY_CLEANUP_INTERVAL = 300  # seconds

# Auto-discovery Configuration
DISCOVERY_TIMEOUT = 5  # seconds
SERVICE_TYPE = "_focusclass._tcp.local."

# Export Configuration
EXPORT_FORMATS = ["csv", "pdf", "json"]
MAX_EXPORT_RECORDS = 10000

# Update Configuration
CHECK_UPDATES = False
UPDATE_URL = "https://api.focusclass.app/updates"

# Platform-specific Configuration
WINDOWS_SPECIFIC = {
    "require_admin": False,  # Set to True for full focus mode
    "use_lightweight_mode": True,  # Use when admin not available
    "focus_assist_enabled": True
}

# Development Configuration
DEBUG_MODE = False
ENABLE_PROFILING = False
MOCK_NETWORK = False

# Tkinter Theme Configuration
TKINTER_THEME = {
    "bg_color": "#f0f0f0",
    "fg_color": "#333333",
    "accent_color": "#007acc",
    "error_color": "#dc3545",
    "success_color": "#28a745",
    "warning_color": "#ffc107",
    "font_family": "Segoe UI",
    "font_size": 10,
    "button_font_size": 9,
    "title_font_size": 14
}