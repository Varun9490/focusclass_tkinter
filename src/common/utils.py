"""
Utility functions for FocusClass Tkinter Application
"""

import asyncio
import logging
import socket
import uuid
import secrets
import hashlib
import json
import time
import qrcode
from io import BytesIO
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import base64
from PIL import Image, ImageTk
import sys
import os
import tkinter as tk
from tkinter import messagebox, filedialog


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        log_level: Logging level
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file) if log_file else logging.NullHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def generate_session_code() -> str:
    """Generate a random session code"""
    return secrets.token_urlsafe(6).upper().replace("-", "").replace("_", "")[:8]


def generate_password() -> str:
    """Generate a random password"""
    return secrets.token_urlsafe(9)


def generate_client_id() -> str:
    """Generate a unique client ID"""
    return str(uuid.uuid4())


def get_local_ip() -> str:
    """Get the local IP address"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def get_machine_info() -> Dict[str, Any]:
    """Get machine information"""
    import platform
    import psutil
    
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "architecture": platform.architecture()[0],
        "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "cpu_count": psutil.cpu_count(),
        "python_version": platform.python_version()
    }


def validate_ip_address(ip: str) -> bool:
    """Validate IP address format"""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def validate_port(port: int) -> bool:
    """Validate port number"""
    return 1 <= port <= 65535


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hash a password with salt
    
    Args:
        password: Password to hash
        salt: Optional salt (generates if not provided)
        
    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine password and salt
    combined = (password + salt).encode('utf-8')
    
    # Hash using SHA-256
    hashed = hashlib.sha256(combined).hexdigest()
    
    return hashed, salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """Verify password against hash"""
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == hashed_password


def create_qr_code(data: Dict[str, Any], size: int = 200) -> Image.Image:
    """
    Create QR code from data
    
    Args:
        data: Data to encode
        size: QR code size in pixels
        
    Returns:
        PIL Image of QR code
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Convert data to JSON string
    qr_data = json.dumps(data)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize to specified size
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    return img


def parse_qr_code_data(qr_data: str) -> Optional[Dict[str, Any]]:
    """Parse QR code data"""
    try:
        data = json.loads(qr_data)
        
        # Validate required fields
        required_fields = ["type", "teacher_ip", "session_code", "password"]
        if all(field in data for field in required_fields):
            return data
        else:
            return None
            
    except (json.JSONDecodeError, KeyError):
        return None


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string"""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    
    image_data = buffer.getvalue()
    base64_str = base64.b64encode(image_data).decode('utf-8')
    
    return f"data:image/png;base64,{base64_str}"


def base64_to_image(base64_str: str) -> Optional[Image.Image]:
    """Convert base64 string to PIL Image"""
    try:
        # Remove data URL prefix if present
        if base64_str.startswith("data:image"):
            base64_str = base64_str.split(",", 1)[1]
        
        image_data = base64.b64decode(base64_str)
        buffer = BytesIO(image_data)
        
        return Image.open(buffer)
        
    except Exception:
        return None


def pil_to_tkinter(image: Image.Image) -> ImageTk.PhotoImage:
    """Convert PIL Image to Tkinter PhotoImage"""
    return ImageTk.PhotoImage(image)


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def ensure_directory(directory: str):
    """Ensure directory exists"""
    Path(directory).mkdir(parents=True, exist_ok=True)


def clean_old_files(directory: str, max_age_days: int = 7):
    """Clean files older than specified days"""
    try:
        directory_path = Path(directory)
        if not directory_path.exists():
            return
        
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                except OSError:
                    pass  # Ignore errors
                    
    except Exception:
        pass  # Ignore errors


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """Safely load JSON with default fallback"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Safely dump JSON with default fallback"""
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return default


def show_error_message(title: str, message: str, parent=None):
    """Show error message dialog"""
    messagebox.showerror(title, message, parent=parent)


def show_info_message(title: str, message: str, parent=None):
    """Show info message dialog"""
    messagebox.showinfo(title, message, parent=parent)


def show_warning_message(title: str, message: str, parent=None):
    """Show warning message dialog"""
    messagebox.showwarning(title, message, parent=parent)


def ask_yes_no(title: str, message: str, parent=None) -> bool:
    """Ask yes/no question"""
    return messagebox.askyesno(title, message, parent=parent)


def ask_ok_cancel(title: str, message: str, parent=None) -> bool:
    """Ask OK/Cancel question"""
    return messagebox.askokcancel(title, message, parent=parent)


def save_file_dialog(title: str = "Save File", filetypes=None, defaultextension="", parent=None) -> Optional[str]:
    """Show save file dialog"""
    if filetypes is None:
        filetypes = [("All files", "*.*")]
    
    return filedialog.asksaveasfilename(
        title=title,
        filetypes=filetypes,
        defaultextension=defaultextension,
        parent=parent
    )


def open_file_dialog(title: str = "Open File", filetypes=None, parent=None) -> Optional[str]:
    """Show open file dialog"""
    if filetypes is None:
        filetypes = [("All files", "*.*")]
    
    return filedialog.askopenfilename(
        title=title,
        filetypes=filetypes,
        parent=parent
    )


def center_window(window: tk.Tk, width: int, height: int):
    """Center window on screen"""
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    window.geometry(f"{width}x{height}+{x}+{y}")


def apply_theme(widget: tk.Widget, theme: Dict[str, Any]):
    """Apply theme to widget"""
    try:
        if hasattr(widget, 'configure'):
            config = {}
            
            # Background color
            if 'bg_color' in theme:
                config['bg'] = theme['bg_color']
            
            # Foreground color
            if 'fg_color' in theme:
                config['fg'] = theme['fg_color']
            
            # Font
            if 'font_family' in theme and 'font_size' in theme:
                config['font'] = (theme['font_family'], theme['font_size'])
            
            if config:
                widget.configure(**config)
                
    except Exception:
        pass  # Ignore theming errors


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Initialize rate limiter
        
        Args:
            max_calls: Maximum calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def is_allowed(self) -> bool:
        """Check if call is allowed"""
        current_time = time.time()
        
        # Remove old calls outside time window
        self.calls = [call_time for call_time in self.calls 
                     if current_time - call_time < self.time_window]
        
        # Check if under limit
        if len(self.calls) < self.max_calls:
            self.calls.append(current_time)
            return True
        
        return False


class PerformanceMonitor:
    """Simple performance monitoring"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.measurements = []
    
    def start(self):
        """Start timing"""
        self.start_time = time.time()
    
    def stop(self) -> float:
        """Stop timing and return duration"""
        if self.start_time is None:
            return 0.0
        
        duration = time.time() - self.start_time
        self.measurements.append(duration)
        self.start_time = None
        
        return duration
    
    def get_stats(self) -> Dict[str, float]:
        """Get performance statistics"""
        if not self.measurements:
            return {}
        
        return {
            "count": len(self.measurements),
            "total": sum(self.measurements),
            "average": sum(self.measurements) / len(self.measurements),
            "min": min(self.measurements),
            "max": max(self.measurements)
        }
    
    def reset(self):
        """Reset measurements"""
        self.measurements.clear()


def retry_async(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for retrying async functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (attempt + 1))
                    continue
            
            raise last_exception
        
        return wrapper
    return decorator


def throttle_async(rate: float):
    """Decorator for throttling async function calls"""
    last_called = 0
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            nonlocal last_called
            
            current_time = time.time()
            time_since_last = current_time - last_called
            
            if time_since_last < rate:
                await asyncio.sleep(rate - time_since_last)
            
            last_called = time.time()
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_available_port(start_port: int = 8000, max_attempts: int = 100) -> Optional[int]:
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except socket.error:
            continue
    
    return None


def is_port_available(port: int, host: str = 'localhost') -> bool:
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return True
    except socket.error:
        return False


class ConfigManager:
    """Simple configuration manager"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config = {}
        self.load()
    
    def load(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
        except Exception:
            self.config = {}
    
    def save(self):
        """Save configuration to file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def update(self, config_dict: Dict[str, Any]):
        """Update configuration with dictionary"""
        self.config.update(config_dict)


# Event system for loose coupling
class EventEmitter:
    """Simple event emitter"""
    
    def __init__(self):
        self.listeners = {}
    
    def on(self, event: str, callback):
        """Add event listener"""
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)
    
    def off(self, event: str, callback):
        """Remove event listener"""
        if event in self.listeners:
            try:
                self.listeners[event].remove(callback)
            except ValueError:
                pass
    
    def emit(self, event: str, *args, **kwargs):
        """Emit event to all listeners"""
        if event in self.listeners:
            for callback in self.listeners[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(*args, **kwargs))
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    # Log error but don't stop other listeners
                    logging.getLogger(__name__).error(f"Error in event listener: {e}")
    
    def emit_async(self, event: str, *args, **kwargs):
        """Emit event asynchronously"""
        async def emit_to_listeners():
            if event in self.listeners:
                tasks = []
                for callback in self.listeners[event]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            tasks.append(callback(*args, **kwargs))
                        else:
                            # Run sync function in executor
                            loop = asyncio.get_event_loop()
                            tasks.append(loop.run_in_executor(None, callback, *args))
                    except Exception as e:
                        logging.getLogger(__name__).error(f"Error preparing event listener: {e}")
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
        
        return asyncio.create_task(emit_to_listeners())


class AsyncTkinterHelper:
    """Helper class to run async functions in tkinter"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.loop = None
        self.running = False
        self.thread = None
        self._cleanup_scheduled = False
    
    def start_async_loop(self):
        """Start async event loop in a separate thread"""
        import threading
        
        def run_loop():
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.running = True
                self.loop.run_forever()
            except Exception as e:
                logging.getLogger(__name__).error(f"Error in async loop: {e}")
            finally:
                self.running = False
        
        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        
        # Schedule periodic check for async tasks
        if not self._cleanup_scheduled:
            self._cleanup_scheduled = True
            self.root.after(100, self._check_async_tasks)
    
    def _check_async_tasks(self):
        """Check for completed async tasks"""
        if self.running and self._cleanup_scheduled:
            try:
                self.root.after(100, self._check_async_tasks)
            except tk.TclError:
                # Widget has been destroyed, stop checking
                self._cleanup_scheduled = False
    
    def run_async(self, coro):
        """Run async coroutine"""
        if self.loop and self.running:
            try:
                asyncio.run_coroutine_threadsafe(coro, self.loop)
            except Exception as e:
                logging.getLogger(__name__).error(f"Error running async coroutine: {e}")
    
    def stop(self):
        """Stop async loop"""
        self.running = False
        self._cleanup_scheduled = False
        
        if self.loop:
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass  # Loop might already be stopped
        
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=1.0)
            except Exception:
                pass  # Thread cleanup failed