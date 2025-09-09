"""
Focus Manager for FocusClass Tkinter Application
Handles Windows restrictions and focus mode enforcement
"""

import asyncio
import logging
import time
import threading
from typing import Callable, List, Optional, Dict, Any
import sys

# Windows-specific imports
if sys.platform == "win32":
    import win32api
    import win32con
    import win32gui
    import win32process
    import win32security
    import win32service
    import win32serviceutil
    import pywintypes
    import ctypes
    from ctypes import wintypes
    import psutil
    import winreg


class FocusManager:
    """Manages focus mode restrictions on Windows for tkinter applications"""
    
    def __init__(self, violation_callback: Optional[Callable] = None):
        """
        Initialize focus manager
        
        Args:
            violation_callback: Function to call when violations are detected
        """
        self.logger = logging.getLogger(__name__)
        self.violation_callback = violation_callback
        
        # Focus mode state
        self.focus_mode_active = False
        self.allowed_windows = set()
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        
        # Violation tracking with throttling
        self.violation_count = 0
        self.last_violation_time = 0
        self.violation_throttle = {}  # For throttling repeated violations
        
        # Windows API components
        self.hook_manager = None
        self.keyboard_hook = None
        self.window_hook = None
        
        # Original Windows settings (for restoration)
        self.original_settings = {}
        
        # Restricted key combinations
        self.restricted_keys = {
            'alt_tab': [win32con.VK_MENU, win32con.VK_TAB],
            'win_key': [win32con.VK_LWIN, win32con.VK_RWIN],
            'ctrl_esc': [win32con.VK_CONTROL, win32con.VK_ESCAPE],
            'ctrl_shift_esc': [win32con.VK_CONTROL, win32con.VK_SHIFT, win32con.VK_ESCAPE],
            'alt_f4': [win32con.VK_MENU, win32con.VK_F4],
            'ctrl_alt_del': [win32con.VK_CONTROL, win32con.VK_MENU, win32con.VK_DELETE]
        }
        
        # Currently pressed keys
        self.pressed_keys = set()
        
        if sys.platform != "win32":
            self.logger.warning("Focus Manager only works on Windows")
    
    def is_windows(self) -> bool:
        """Check if running on Windows"""
        return sys.platform == "win32"
    
    async def enable_focus_mode(self, allowed_window_titles: List[str] = None) -> bool:
        """
        Enable focus mode with restrictions
        
        Args:
            allowed_window_titles: List of window titles that are allowed to be active
            
        Returns:
            Success status
        """
        if not self.is_windows():
            self.logger.error("Focus mode only supported on Windows")
            return False
        
        try:
            self.focus_mode_active = True
            self.allowed_windows = set(allowed_window_titles or ["FocusClass Student", "FocusClass Teacher"])
            
            # Install keyboard hooks
            await self._install_keyboard_hook()
            
            # Install window hooks
            await self._install_window_hook()
            
            # Configure Windows Focus Assist
            await self._enable_focus_assist()
            
            # Disable task switching
            await self._disable_task_switching()
            
            # Start monitoring thread
            self._start_monitoring()
            
            self.logger.info("Focus mode enabled")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enable focus mode: {e}")
            await self.disable_focus_mode()
            return False
    
    async def disable_focus_mode(self) -> bool:
        """
        Disable focus mode and restore normal functionality
        
        Returns:
            Success status
        """
        if not self.is_windows():
            return True
        
        try:
            self.focus_mode_active = False
            
            # Stop monitoring
            self._stop_monitoring()
            
            # Remove hooks
            await self._remove_keyboard_hook()
            await self._remove_window_hook()
            
            # Restore Windows settings
            await self._restore_windows_settings()
            
            # Disable Focus Assist
            await self._disable_focus_assist()
            
            self.logger.info("Focus mode disabled")
            return True
            
        except Exception as e:
            self.logger.error(f"Error disabling focus mode: {e}")
            return False
    
    async def _install_keyboard_hook(self):
        """Install low-level keyboard hook"""
        try:
            # Define hook procedure
            def keyboard_hook_proc(nCode, wParam, lParam):
                if nCode >= 0:
                    if wParam in [win32con.WM_KEYDOWN, win32con.WM_SYSKEYDOWN]:
                        vk_code = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_int)).contents.value
                        self.pressed_keys.add(vk_code)
                        
                        # Check for restricted key combinations
                        if self._check_restricted_keys():
                            self._log_violation("keyboard", f"Restricted key combination detected")
                            return 1  # Block the key
                    
                    elif wParam in [win32con.WM_KEYUP, win32con.WM_SYSKEYUP]:
                        vk_code = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_int)).contents.value
                        self.pressed_keys.discard(vk_code)
                
                return ctypes.windll.user32.CallNextHookExW(self.keyboard_hook, nCode, wParam, lParam)
            
            # Install hook
            hook_id = win32gui.SetWindowsHookEx(
                win32con.WH_KEYBOARD_LL,
                keyboard_hook_proc,
                win32api.GetModuleHandle(None),
                0
            )
            
            self.keyboard_hook = hook_id
            self.logger.info("Keyboard hook installed")
            
        except Exception as e:
            self.logger.error(f"Failed to install keyboard hook: {e}")
    
    async def _remove_keyboard_hook(self):
        """Remove keyboard hook"""
        try:
            if self.keyboard_hook:
                win32gui.UnhookWindowsHookEx(self.keyboard_hook)
                self.keyboard_hook = None
                self.logger.info("Keyboard hook removed")
        except Exception as e:
            self.logger.error(f"Error removing keyboard hook: {e}")
    
    async def _install_window_hook(self):
        """Install window event hook"""
        try:
            def window_hook_proc(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
                if event == win32con.EVENT_SYSTEM_FOREGROUND:
                    try:
                        window_title = win32gui.GetWindowText(hwnd)
                        if window_title and not self._is_window_allowed(window_title):
                            self._log_violation("window_switch", f"Switched to unauthorized window: {window_title}")
                            
                            # Try to bring allowed window back to focus
                            self._focus_allowed_window()
                            
                    except Exception as e:
                        self.logger.error(f"Error in window hook: {e}")
            
            # Install window event hook
            self.window_hook = win32gui.SetWinEventHook(
                win32con.EVENT_SYSTEM_FOREGROUND,
                win32con.EVENT_SYSTEM_FOREGROUND,
                0,
                window_hook_proc,
                0,
                0,
                win32con.WINEVENT_OUTOFCONTEXT
            )
            
            self.logger.info("Window hook installed")
            
        except Exception as e:
            self.logger.error(f"Failed to install window hook: {e}")
    
    async def _remove_window_hook(self):
        """Remove window hook"""
        try:
            if self.window_hook:
                win32gui.UnhookWinEventHook(self.window_hook)
                self.window_hook = None
                self.logger.info("Window hook removed")
        except Exception as e:
            self.logger.error(f"Error removing window hook: {e}")
    
    def _check_restricted_keys(self) -> bool:
        """Check if any restricted key combination is pressed"""
        try:
            # Check for Alt+Tab
            if (win32con.VK_MENU in self.pressed_keys and 
                win32con.VK_TAB in self.pressed_keys):
                return True
            
            # Check for Windows key combinations
            if (win32con.VK_LWIN in self.pressed_keys or 
                win32con.VK_RWIN in self.pressed_keys):
                return True
            
            # Check for Ctrl+Esc (Start menu)
            if (win32con.VK_CONTROL in self.pressed_keys and 
                win32con.VK_ESCAPE in self.pressed_keys):
                return True
            
            # Check for Ctrl+Shift+Esc (Task Manager)
            if (win32con.VK_CONTROL in self.pressed_keys and 
                win32con.VK_SHIFT in self.pressed_keys and 
                win32con.VK_ESCAPE in self.pressed_keys):
                return True
            
            # Check for Alt+F4
            if (win32con.VK_MENU in self.pressed_keys and 
                win32con.VK_F4 in self.pressed_keys):
                return True
            
            # Check for F11 (fullscreen toggle)
            if win32con.VK_F11 in self.pressed_keys:
                return True
            
            # Check for Ctrl+N (new window)
            if (win32con.VK_CONTROL in self.pressed_keys and 
                ord('N') in self.pressed_keys):
                return True
            
            # Check for Ctrl+T (new tab)
            if (win32con.VK_CONTROL in self.pressed_keys and 
                ord('T') in self.pressed_keys):
                return True
            
            # Check for Ctrl+W (close tab)
            if (win32con.VK_CONTROL in self.pressed_keys and 
                ord('W') in self.pressed_keys):
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking restricted keys: {e}")
            return False
    
    def _log_violation(self, violation_type: str, description: str):
        """Log a focus mode violation with throttling"""
        try:
            current_time = time.time()
            
            # Create throttle key
            throttle_key = f"{violation_type}_{description}"
            
            # Check throttling (5 second cooldown per violation type)
            if throttle_key in self.violation_throttle:
                last_time, count = self.violation_throttle[throttle_key]
                if current_time - last_time < 5.0:
                    # Within cooldown period
                    if count >= 3:
                        # Silent logging to database, but don't show in UI
                        self.violation_throttle[throttle_key] = (last_time, count + 1)
                        return
                    else:
                        # Increment count and continue with logging
                        self.violation_throttle[throttle_key] = (last_time, count + 1)
                else:
                    # Reset counter after cooldown
                    self.violation_throttle[throttle_key] = (current_time, 1)
            else:
                # First occurrence
                self.violation_throttle[throttle_key] = (current_time, 1)
            
            self.last_violation_time = current_time
            self.violation_count += 1
            
            # Get current count for display
            _, count = self.violation_throttle[throttle_key]
            
            violation_data = {
                "type": violation_type,
                "description": description,
                "timestamp": current_time,
                "violation_count": self.violation_count,
                "repeat_count": count
            }
            
            # Format display message with count
            display_description = description
            if count > 1:
                display_description += f" (x{count})"
            
            self.logger.warning(f"Focus violation: {violation_type} - {display_description}")
            
            # Call violation callback
            if self.violation_callback:
                asyncio.create_task(self.violation_callback(violation_data))
                
        except Exception as e:
            self.logger.error(f"Error logging violation: {e}")
    
    def _start_monitoring(self):
        """Start the monitoring thread"""
        try:
            self.stop_monitoring.clear()
            self.monitoring_thread = threading.Thread(
                target=self._monitor_windows,
                daemon=True
            )
            self.monitoring_thread.start()
            self.logger.info("Window monitoring started")
            
        except Exception as e:
            self.logger.error(f"Error starting monitoring: {e}")
    
    def _stop_monitoring(self):
        """Stop the monitoring thread"""
        try:
            self.stop_monitoring.set()
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=2.0)
            self.logger.info("Window monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping monitoring: {e}")
    
    def _monitor_windows(self):
        """Monitor active windows for violations"""
        try:
            while not self.stop_monitoring.is_set():
                try:
                    # Get the current foreground window
                    hwnd = win32gui.GetForegroundWindow()
                    window_title = win32gui.GetWindowText(hwnd)
                    
                    # Check if the current window is allowed
                    if window_title and not self._is_window_allowed(window_title):
                        # Try to bring allowed window to front
                        allowed_hwnd = self._find_allowed_window()
                        if allowed_hwnd:
                            win32gui.SetForegroundWindow(allowed_hwnd)
                            win32gui.ShowWindow(allowed_hwnd, win32con.SW_RESTORE)
                        
                        self._log_violation("window_switch", f"Attempted to switch to: {window_title}")
                    
                    # Check for new browser tabs or windows
                    self._check_browser_violations()
                    
                    # Check for unauthorized processes
                    self._check_unauthorized_processes()
                    
                    # Sleep briefly to avoid excessive CPU usage
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"Error in window monitoring loop: {e}")
                    time.sleep(1.0)
        
        except Exception as e:
            self.logger.error(f"Error in window monitoring: {e}")
    
    def _is_window_allowed(self, window_title: str) -> bool:
        """Check if a window title is in the allowed list"""
        for allowed in self.allowed_windows:
            if allowed.lower() in window_title.lower():
                return True
        
        # Always allow system windows
        system_windows = [
            "Program Manager",
            "Desktop Window Manager",
            "Windows Security",
            "Task Manager"
        ]
        
        for system_window in system_windows:
            if system_window.lower() in window_title.lower():
                return True
        
        return False
    
    def _find_allowed_window(self) -> Optional[int]:
        """Find an allowed window handle"""
        try:
            def enum_window_callback(hwnd, allowed_handles):
                window_title = win32gui.GetWindowText(hwnd)
                if window_title and self._is_window_allowed(window_title):
                    if win32gui.IsWindowVisible(hwnd):
                        allowed_handles.append(hwnd)
                return True
            
            allowed_handles = []
            win32gui.EnumWindows(enum_window_callback, allowed_handles)
            
            return allowed_handles[0] if allowed_handles else None
            
        except Exception as e:
            self.logger.error(f"Error finding allowed window: {e}")
            return None
    
    def _focus_allowed_window(self):
        """Bring an allowed window to focus"""
        try:
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    if self._is_window_allowed(window_title):
                        windows.append((hwnd, window_title))
                return True
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            if windows:
                # Focus the first allowed window
                hwnd, title = windows[0]
                win32gui.SetForegroundWindow(hwnd)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                self.logger.info(f"Refocused to allowed window: {title}")
            
        except Exception as e:
            self.logger.error(f"Error focusing allowed window: {e}")
    
    def _check_browser_violations(self):
        """Check for browser-based violations (new tabs, etc.)"""
        try:
            # Get all running processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_name = proc.info['name'].lower()
                    
                    # Check for browsers
                    if any(browser in proc_name for browser in 
                           ['chrome', 'firefox', 'edge', 'opera', 'safari', 'brave']):
                        
                        # Check command line for multiple tabs/windows
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline and len(cmdline) > 5:  # Likely multiple tabs
                            # Count chrome processes (each tab is a process in Chrome)
                            chrome_count = sum(1 for p in psutil.process_iter(['name']) 
                                              if 'chrome' in p.info['name'].lower())
                            
                            if chrome_count > 3:  # More than typical for single tab
                                self._log_violation("browser_tabs", 
                                                   f"Multiple browser tabs/windows detected ({chrome_count} processes)")
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"Error checking browser violations: {e}")
    
    def _check_unauthorized_processes(self):
        """Check for unauthorized processes"""
        try:
            # List of processes that should be blocked during focus mode
            blocked_processes = [
                "taskmgr.exe",      # Task Manager
                "cmd.exe",          # Command Prompt
                "powershell.exe",   # PowerShell
                "regedit.exe",      # Registry Editor
                "msconfig.exe",     # System Configuration
                "control.exe",      # Control Panel
                "dxdiag.exe",       # DirectX Diagnostic
                "msinfo32.exe",     # System Information
            ]
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() in [p.lower() for p in blocked_processes]:
                        self._log_violation("unauthorized_process", 
                                          f"Unauthorized process detected: {proc.info['name']}")
                        
                        # Optionally terminate the process (requires admin privileges)
                        # proc.terminate()
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error checking processes: {e}")
    
    async def _disable_task_switching(self):
        """Disable task switching via registry and other methods"""
        try:
            # Disable Task Manager via registry
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                    "Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", 
                                    0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(key)
                self.original_settings["DisableTaskMgr"] = True
                self.logger.info("Task Manager disabled")
            except Exception as e:
                self.logger.warning(f"Could not disable Task Manager: {e}")
            
        except Exception as e:
            self.logger.error(f"Error disabling task switching: {e}")
    
    async def _enable_focus_assist(self):
        """Enable Windows Focus Assist"""
        try:
            # Use Windows Focus Assist API if available
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                "Software\\Microsoft\\Windows\\CurrentVersion\\CloudStore\\Store\\Cache\\DefaultAccount",
                                0, winreg.KEY_SET_VALUE)
            # Enable Focus Assist in Priority mode
            winreg.SetValueEx(key, "QuietMode", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.logger.info("Focus Assist enabled")
            
        except Exception as e:
            self.logger.warning(f"Could not enable Focus Assist: {e}")
    
    async def _disable_focus_assist(self):
        """Disable Windows Focus Assist"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                "Software\\Microsoft\\Windows\\CurrentVersion\\CloudStore\\Store\\Cache\\DefaultAccount",
                                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "QuietMode", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            self.logger.info("Focus Assist disabled")
            
        except Exception as e:
            self.logger.warning(f"Could not disable Focus Assist: {e}")
    
    async def _restore_windows_settings(self):
        """Restore original Windows settings"""
        try:
            # Restore Task Manager
            if self.original_settings.get("DisableTaskMgr"):
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        "Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
                                        0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, "DisableTaskMgr")
                    winreg.CloseKey(key)
                    self.logger.info("Task Manager restored")
                except Exception as e:
                    self.logger.warning(f"Could not restore Task Manager: {e}")
            
            self.original_settings.clear()
            
        except Exception as e:
            self.logger.error(f"Error restoring Windows settings: {e}")
    
    # Public methods for external control
    def add_allowed_window(self, window_title: str):
        """Add a window to the allowed list"""
        self.allowed_windows.add(window_title)
        self.logger.info(f"Added allowed window: {window_title}")
    
    def remove_allowed_window(self, window_title: str):
        """Remove a window from the allowed list"""
        self.allowed_windows.discard(window_title)
        self.logger.info(f"Removed allowed window: {window_title}")
    
    def get_violation_count(self) -> int:
        """Get current violation count"""
        return self.violation_count
    
    def reset_violation_count(self):
        """Reset violation count"""
        self.violation_count = 0
        self.violation_throttle.clear()
        self.logger.info("Violation count reset")
    
    def is_focus_mode_active(self) -> bool:
        """Check if focus mode is currently active"""
        return self.focus_mode_active
    
    # Utility methods
    def get_current_window_title(self) -> str:
        """Get title of currently focused window"""
        try:
            if self.is_windows():
                foreground_window = win32gui.GetForegroundWindow()
                return win32gui.GetWindowText(foreground_window)
            return ""
        except Exception:
            return ""
    
    def get_running_processes(self) -> List[Dict[str, Any]]:
        """Get list of currently running processes"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"Error getting processes: {e}")
        
        return processes
    
    async def cleanup(self):
        """Clean up resources"""
        await self.disable_focus_mode()
        self.logger.info("Focus manager cleaned up")


# Helper functions
def is_admin():
    """Check if running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def request_admin_privileges():
    """Request administrator privileges"""
    if not is_admin():
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return False
    return True


class LightweightFocusManager:
    """Lightweight focus manager for systems without admin privileges"""
    
    def __init__(self, violation_callback: Optional[Callable] = None):
        self.logger = logging.getLogger(__name__)
        self.violation_callback = violation_callback
        self.focus_mode_active = False
        self.allowed_windows = set()
        self.monitoring_task = None
        
    async def enable_focus_mode(self, allowed_window_titles: List[str] = None) -> bool:
        """Enable lightweight focus mode"""
        self.focus_mode_active = True
        self.allowed_windows = set(allowed_window_titles or ["FocusClass Student", "FocusClass Teacher"])
        
        # Only basic window monitoring without hooks
        self.monitoring_task = asyncio.create_task(self._monitor_windows())
        
        self.logger.info("Lightweight focus mode enabled")
        return True
    
    async def disable_focus_mode(self) -> bool:
        """Disable lightweight focus mode"""
        self.focus_mode_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            
        self.logger.info("Lightweight focus mode disabled")
        return True
    
    async def _monitor_windows(self):
        """Monitor windows without hooks"""
        while self.focus_mode_active:
            try:
                if sys.platform == "win32":
                    foreground_window = win32gui.GetForegroundWindow()
                    window_title = win32gui.GetWindowText(foreground_window)
                    
                    if window_title and not self._is_window_allowed(window_title):
                        await self._log_violation("window_switch", 
                                                f"Switched to unauthorized window: {window_title}")
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                self.logger.error(f"Error monitoring windows: {e}")
                await asyncio.sleep(5)
    
    def _is_window_allowed(self, window_title: str) -> bool:
        """Check if window is allowed"""
        for allowed in self.allowed_windows:
            if allowed.lower() in window_title.lower():
                return True
        return False
    
    async def _log_violation(self, violation_type: str, description: str):
        """Log violation"""
        if self.violation_callback:
            await self.violation_callback({
                "type": violation_type,
                "description": description,
                "timestamp": time.time()
            })
    
    def is_focus_mode_active(self) -> bool:
        return self.focus_mode_active
    
    async def cleanup(self):
        await self.disable_focus_mode()