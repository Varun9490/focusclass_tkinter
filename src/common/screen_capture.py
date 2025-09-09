"""
Screen Capture Manager for FocusClass Tkinter Application
Handles screen recording, streaming, and image display in tkinter
"""

import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Tuple, List
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk
import tkinter as tk

# Screen capture
import mss
try:
    import pyautogui
except ImportError:
    pyautogui = None
    print("Warning: pyautogui not available.")

# WebRTC imports with fallbacks
try:
    from aiortc import MediaStreamTrack, VideoStreamTrack
    from aiortc.contrib.media import MediaPlayer
    from av import VideoFrame
    import fractions
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    print("Warning: aiortc/av not available. WebRTC screen sharing will be disabled.")
    
    # Create dummy classes for compatibility
    class VideoStreamTrack:
        kind = "video"
        def __init__(self): pass
        async def recv(self): return None
    
    class MediaStreamTrack:
        def __init__(self): pass
    
    class VideoFrame:
        @staticmethod
        def from_ndarray(array, format): return None
    
    class MediaPlayer:
        def __init__(self, *args, **kwargs): pass
    
    import fractions


class ScreenCaptureTrack(VideoStreamTrack):
    """Custom video track for screen capture (WebRTC compatible)"""
    
    kind = "video"
    
    def __init__(self, monitor: int = 0, fps: int = 15, scale_factor: float = 1.0):
        """
        Initialize screen capture track
        
        Args:
            monitor: Monitor number to capture (0 = primary)
            fps: Frames per second
            scale_factor: Scale factor for resolution (1.0 = original size)
        """
        if WEBRTC_AVAILABLE:
            super().__init__()
        
        self.monitor = monitor
        self.fps = fps
        self.scale_factor = scale_factor
        self.logger = logging.getLogger(__name__)
        
        # Screen capture setup
        self.sct = mss.mss()
        self.monitor_info = self.sct.monitors[monitor + 1]  # 0 is all monitors
        
        # Calculate scaled dimensions
        self.width = int(self.monitor_info["width"] * scale_factor)
        self.height = int(self.monitor_info["height"] * scale_factor)
        
        # Frame timing
        self.frame_duration = 1.0 / fps
        self.last_frame_time = 0
        
        # Performance tracking
        self.frame_count = 0
        self.capture_times = []
        
        self.logger.info(f"Screen capture initialized: {self.width}x{self.height} @ {fps}fps")
    
    async def recv(self):
        """Receive next video frame (for WebRTC)"""
        if not WEBRTC_AVAILABLE:
            self.logger.warning("WebRTC not available. Cannot provide video frames.")
            await asyncio.sleep(1)  # Prevent tight loop
            return None
            
        # Control frame rate
        current_time = time.time()
        if current_time - self.last_frame_time < self.frame_duration:
            await asyncio.sleep(self.frame_duration - (current_time - self.last_frame_time))
        
        start_time = time.time()
        
        try:
            # Capture screen
            screenshot = self.sct.grab(self.monitor_info)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            # Scale if necessary
            if self.scale_factor != 1.0:
                img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
            
            # Convert to numpy array
            img_array = np.array(img)
            
            # Create VideoFrame
            if WEBRTC_AVAILABLE:
                frame = VideoFrame.from_ndarray(img_array, format="rgb24")
                frame.pts = self.frame_count
                frame.time_base = fractions.Fraction(1, self.fps)
            else:
                frame = None
            
            # Performance tracking
            capture_time = time.time() - start_time
            self.capture_times.append(capture_time)
            if len(self.capture_times) > 100:
                self.capture_times.pop(0)
            
            self.frame_count += 1
            self.last_frame_time = current_time
            
            return frame
            
        except Exception as e:
            self.logger.error(f"Error capturing screen: {e}")
            # Return a black frame on error
            if WEBRTC_AVAILABLE:
                black_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                frame = VideoFrame.from_ndarray(black_frame, format="rgb24")
                frame.pts = self.frame_count
                frame.time_base = fractions.Fraction(1, self.fps)
                self.frame_count += 1
                return frame
            else:
                return None
    
    def get_performance_stats(self) -> dict:
        """Get performance statistics"""
        if not self.capture_times:
            return {}
        
        avg_capture_time = sum(self.capture_times) / len(self.capture_times)
        max_capture_time = max(self.capture_times)
        
        return {
            "avg_capture_time": avg_capture_time,
            "max_capture_time": max_capture_time,
            "actual_fps": 1.0 / avg_capture_time if avg_capture_time > 0 else 0,
            "frame_count": self.frame_count
        }


class TkinterScreenCapture:
    """Screen capture manager specifically for tkinter display"""
    
    def __init__(self, display_widget: Optional[tk.Label] = None):
        """
        Initialize tkinter screen capture
        
        Args:
            display_widget: tkinter Label widget to display captured frames
        """
        self.logger = logging.getLogger(__name__)
        self.display_widget = display_widget
        
        # Capture state
        self.is_capturing = False
        self.capture_thread = None
        self.stop_capture_event = threading.Event()
        
        # Capture settings
        self.monitor = 0
        self.fps = 15
        self.scale_factor = 0.5  # Smaller scale for tkinter display
        self.display_size = (640, 480)  # Target display size
        
        # Current frame
        self.current_frame = None
        self.current_tk_image = None
        
        # Frame callback
        self.frame_callback = None
        
        # Screen capture
        self.sct = mss.mss()
        self.monitors = self.sct.monitors[1:]  # Skip "All monitors"
        
        self.logger.info(f"Tkinter screen capture initialized with {len(self.monitors)} monitors")
    
    def set_display_widget(self, widget: tk.Label):
        """Set the display widget"""
        self.display_widget = widget
    
    def set_display_size(self, width: int, height: int):
        """Set target display size"""
        self.display_size = (width, height)
        self.logger.info(f"Display size set to {width}x{height}")
    
    def set_monitor(self, monitor_index: int):
        """Set monitor to capture"""
        if 0 <= monitor_index < len(self.monitors):
            self.monitor = monitor_index
            self.logger.info(f"Monitor set to {monitor_index}")
        else:
            self.logger.warning(f"Invalid monitor index: {monitor_index}")
    
    def start_capture(self) -> bool:
        """Start capturing screen"""
        if self.is_capturing:
            self.logger.warning("Screen capture already active")
            return True
        
        try:
            self.is_capturing = True
            self.stop_capture_event.clear()
            
            # Start capture thread
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            self.logger.info(f"Tkinter screen capture started for monitor {self.monitor}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start screen capture: {e}")
            self.is_capturing = False
            return False
    
    def stop_capture(self):
        """Stop capturing screen"""
        if not self.is_capturing:
            return
        
        self.is_capturing = False
        self.stop_capture_event.set()
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        self.logger.info("Tkinter screen capture stopped")
    
    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        frame_duration = 1.0 / self.fps
        
        while not self.stop_capture_event.is_set():
            start_time = time.time()
            
            try:
                # Capture frame
                frame = self._capture_frame()
                if frame:
                    self.current_frame = frame
                    
                    # Convert to tkinter format
                    tk_image = ImageTk.PhotoImage(frame)
                    self.current_tk_image = tk_image
                    
                    # Update display widget if available
                    if self.display_widget:
                        try:
                            self.display_widget.configure(image=tk_image)
                            self.display_widget.image = tk_image  # Keep reference
                        except Exception as e:
                            self.logger.error(f"Error updating display widget: {e}")
                    
                    # Call frame callback if available
                    if self.frame_callback:
                        try:
                            self.frame_callback(frame, tk_image)
                        except Exception as e:
                            self.logger.error(f"Error in frame callback: {e}")
                
                # Control frame rate
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_duration - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)  # Brief pause on error
    
    def _capture_frame(self) -> Optional[Image.Image]:
        """Capture a single frame"""
        try:
            if self.monitor >= len(self.monitors):
                return None
            
            # Get monitor info
            monitor_info = self.monitors[self.monitor]
            
            # Capture screen
            screenshot = self.sct.grab(monitor_info)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            # Resize to display size
            img = img.resize(self.display_size, Image.Resampling.LANCZOS)
            
            return img
            
        except Exception as e:
            self.logger.error(f"Error capturing frame: {e}")
            return None
    
    def get_current_frame(self) -> Optional[Image.Image]:
        """Get current frame as PIL Image"""
        return self.current_frame
    
    def get_current_tk_image(self) -> Optional[ImageTk.PhotoImage]:
        """Get current frame as tkinter PhotoImage"""
        return self.current_tk_image
    
    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[Image.Image]:
        """Take a single screenshot"""
        try:
            if self.monitor >= len(self.monitors):
                return None
            
            monitor_info = self.monitors[self.monitor]
            screenshot = self.sct.grab(monitor_info)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            if save_path:
                img.save(save_path)
                self.logger.info(f"Screenshot saved to {save_path}")
            
            return img
            
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return None
    
    def register_frame_callback(self, callback: Callable):
        """Register callback for new frames"""
        self.frame_callback = callback
    
    def get_monitors(self) -> List[dict]:
        """Get list of available monitors"""
        return self.monitors.copy()


class ScreenCapture:
    """Main screen capture manager with both WebRTC and tkinter support"""
    
    def __init__(self):
        """Initialize screen capture manager"""
        self.logger = logging.getLogger(__name__)
        
        # Capture state
        self.is_capturing = False
        self.capture_track = None
        self.tkinter_capture = None
        
        # Available monitors
        self.monitors = []
        self._detect_monitors()
        
        # Capture settings
        self.current_monitor = 0
        self.fps = 15
        self.scale_factor = 1.0
        self.quality = "medium"
        
        # Quality presets
        self.quality_presets = {
            "low": {"fps": 10, "scale": 0.5},
            "medium": {"fps": 15, "scale": 0.75},
            "high": {"fps": 20, "scale": 1.0},
            "ultra": {"fps": 30, "scale": 1.0}
        }
        
        # Callbacks
        self.frame_callback = None
        
    def _detect_monitors(self):
        """Detect available monitors"""
        try:
            with mss.mss() as sct:
                self.monitors = sct.monitors[1:]  # Skip the "All monitors" entry
                
            self.logger.info(f"Detected {len(self.monitors)} monitors")
            for i, monitor in enumerate(self.monitors):
                self.logger.info(f"Monitor {i}: {monitor['width']}x{monitor['height']} "
                               f"at ({monitor['left']}, {monitor['top']})")
                
        except Exception as e:
            self.logger.error(f"Error detecting monitors: {e}")
            # Fallback to primary monitor
            self.monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080}]
    
    def get_monitors(self) -> List[dict]:
        """Get list of available monitors"""
        return self.monitors.copy()
    
    def set_quality(self, quality: str):
        """Set capture quality preset"""
        if quality in self.quality_presets:
            preset = self.quality_presets[quality]
            self.fps = preset["fps"]
            self.scale_factor = preset["scale"]
            self.quality = quality
            self.logger.info(f"Quality set to {quality}: {self.fps}fps, scale={self.scale_factor}")
        else:
            self.logger.warning(f"Unknown quality preset: {quality}")
    
    def set_custom_settings(self, fps: int, scale_factor: float):
        """Set custom capture settings"""
        self.fps = max(1, min(60, fps))  # Limit between 1-60 fps
        self.scale_factor = max(0.1, min(2.0, scale_factor))  # Limit scale factor
        self.quality = "custom"
        self.logger.info(f"Custom settings: {self.fps}fps, scale={self.scale_factor}")
    
    def start_webrtc_capture(self, monitor: int = 0) -> Optional[ScreenCaptureTrack]:
        """
        Start WebRTC screen capture
        
        Args:
            monitor: Monitor index to capture
            
        Returns:
            Screen capture track for WebRTC (or None if WebRTC unavailable)
        """
        if self.is_capturing:
            self.logger.warning("Screen capture already active")
            return self.capture_track
        
        if monitor >= len(self.monitors):
            self.logger.error(f"Monitor {monitor} not available")
            return None
            
        try:
            self.current_monitor = monitor
            
            if WEBRTC_AVAILABLE:
                # Full WebRTC mode
                self.capture_track = ScreenCaptureTrack(
                    monitor=monitor,
                    fps=self.fps,
                    scale_factor=self.scale_factor
                )
                self.is_capturing = True
                self.logger.info(f"WebRTC screen capture started for monitor {monitor}")
                return self.capture_track
            else:
                self.logger.warning("WebRTC not available for screen capture")
                return None
            
        except Exception as e:
            self.logger.error(f"Failed to start WebRTC screen capture: {e}")
            return None
    
    def start_tkinter_capture(self, monitor: int = 0, display_widget: Optional[tk.Label] = None) -> bool:
        """
        Start tkinter screen capture
        
        Args:
            monitor: Monitor index to capture
            display_widget: Optional tkinter widget to display frames
            
        Returns:
            Success status
        """
        if self.is_capturing:
            self.logger.warning("Screen capture already active")
            return True
        
        if monitor >= len(self.monitors):
            self.logger.error(f"Monitor {monitor} not available")
            return False
            
        try:
            self.current_monitor = monitor
            self.tkinter_capture = TkinterScreenCapture(display_widget)
            self.tkinter_capture.set_monitor(monitor)
            
            # Apply quality settings
            self.tkinter_capture.fps = self.fps
            
            success = self.tkinter_capture.start_capture()
            if success:
                self.is_capturing = True
                self.logger.info(f"Tkinter screen capture started for monitor {monitor}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to start tkinter screen capture: {e}")
            return False
    
    def stop_capture(self):
        """Stop screen capture"""
        if not self.is_capturing:
            return
        
        self.is_capturing = False
        
        if self.tkinter_capture:
            self.tkinter_capture.stop_capture()
            self.tkinter_capture = None
        
        self.capture_track = None
        
        self.logger.info("Screen capture stopped")
    
    def take_screenshot(self, monitor: int = 0, save_path: Optional[str] = None) -> Optional[Image.Image]:
        """
        Take a single screenshot
        
        Args:
            monitor: Monitor index
            save_path: Optional path to save image
            
        Returns:
            PIL Image object
        """
        try:
            with mss.mss() as sct:
                if monitor >= len(self.monitors):
                    monitor = 0
                
                monitor_info = sct.monitors[monitor + 1]
                screenshot = sct.grab(monitor_info)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                if save_path:
                    img.save(save_path)
                    self.logger.info(f"Screenshot saved to {save_path}")
                
                return img
                
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return None
    
    def get_current_frame(self) -> Optional[Image.Image]:
        """Get current frame from tkinter capture"""
        if self.tkinter_capture:
            return self.tkinter_capture.get_current_frame()
        return None
    
    def get_current_tk_image(self) -> Optional[ImageTk.PhotoImage]:
        """Get current frame as tkinter PhotoImage"""
        if self.tkinter_capture:
            return self.tkinter_capture.get_current_tk_image()
        return None
    
    def get_capture_stats(self) -> dict:
        """Get capture performance statistics"""
        if not self.is_capturing:
            return {}
        
        stats = {
            "monitor": self.current_monitor,
            "quality": self.quality,
            "target_fps": self.fps,
            "scale_factor": self.scale_factor,
            "mode": "webrtc" if self.capture_track else "tkinter"
        }
        
        if WEBRTC_AVAILABLE and self.capture_track and hasattr(self.capture_track, 'get_performance_stats'):
            stats.update(self.capture_track.get_performance_stats())
        
        return stats
    
    def register_frame_callback(self, callback: Callable):
        """Register callback for frame events"""
        self.frame_callback = callback
        if self.tkinter_capture:
            self.tkinter_capture.register_frame_callback(callback)


class StudentScreenShare:
    """Handles student screen sharing requests for tkinter"""
    
    def __init__(self, approval_callback: Optional[Callable] = None):
        """
        Initialize student screen share
        
        Args:
            approval_callback: Function to call for approval requests
        """
        self.logger = logging.getLogger(__name__)
        self.approval_callback = approval_callback
        
        # Sharing state
        self.is_sharing = False
        self.share_capture = None
        
        # Auto-approval settings
        self.auto_approve = False
        self.require_confirmation = True
        
        # Screen capture for sharing
        self.screen_capture = ScreenCapture()
    
    async def handle_share_request(self, request_data: dict) -> dict:
        """
        Handle screen share request from teacher
        
        Args:
            request_data: Request details
            
        Returns:
            Response data
        """
        try:
            if self.auto_approve and not self.require_confirmation:
                # Auto-approve without user interaction
                success = await self._start_sharing()
                return {
                    "success": success,
                    "message": "Screen sharing started automatically" if success else "Failed to start sharing"
                }
            
            # Request user approval
            if self.approval_callback:
                approved = await self.approval_callback(request_data)
                if approved:
                    success = await self._start_sharing()
                    return {
                        "success": success,
                        "message": "Screen sharing started" if success else "Failed to start sharing"
                    }
                else:
                    return {
                        "success": False,
                        "message": "Screen sharing denied by user"
                    }
            else:
                # No approval mechanism - deny by default
                return {
                    "success": False,
                    "message": "Screen sharing not configured"
                }
                
        except Exception as e:
            self.logger.error(f"Error handling share request: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }
    
    async def _start_sharing(self) -> bool:
        """Start screen sharing"""
        try:
            if self.is_sharing:
                self.logger.warning("Screen sharing already active")
                return True
            
            # Start screen capture with lower quality for sharing
            self.screen_capture.set_quality("medium")
            
            # Try WebRTC first, fallback to tkinter
            self.share_capture = self.screen_capture.start_webrtc_capture()
            if not self.share_capture:
                # Fallback to tkinter capture
                success = self.screen_capture.start_tkinter_capture()
                if not success:
                    return False
            
            self.is_sharing = True
            self.logger.info("Student screen sharing started")
            return True
                
        except Exception as e:
            self.logger.error(f"Error starting screen sharing: {e}")
            return False
    
    async def stop_sharing(self):
        """Stop screen sharing"""
        if not self.is_sharing:
            return
        
        try:
            self.screen_capture.stop_capture()
            self.share_capture = None
            self.is_sharing = False
            
            self.logger.info("Student screen sharing stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping screen sharing: {e}")
    
    def get_share_track(self) -> Optional[ScreenCaptureTrack]:
        """Get the current share track for WebRTC"""
        return self.share_capture if self.is_sharing else None
    
    def set_auto_approve(self, auto_approve: bool, require_confirmation: bool = True):
        """Set auto-approval settings"""
        self.auto_approve = auto_approve
        self.require_confirmation = require_confirmation
        
        self.logger.info(f"Auto-approve: {auto_approve}, Require confirmation: {require_confirmation}")


# Utility functions
def optimize_for_lan():
    """Optimize screen capture settings for LAN"""
    return {
        "fps": 20,
        "scale_factor": 0.8,
        "quality": "high"
    }


def optimize_for_internet():
    """Optimize screen capture settings for internet"""
    return {
        "fps": 10,
        "scale_factor": 0.5,
        "quality": "low"
    }


def get_optimal_resolution(monitor_resolution: Tuple[int, int], 
                          connection_type: str = "lan") -> Tuple[int, int]:
    """Get optimal resolution based on connection type"""
    width, height = monitor_resolution
    
    if connection_type == "lan":
        # Higher resolution for LAN
        scale = 0.75 if width > 1920 else 1.0
    else:
        # Lower resolution for internet
        scale = 0.5 if width > 1920 else 0.6
    
    return (int(width * scale), int(height * scale))


def create_screen_preview_widget(parent: tk.Widget, width: int = 640, height: int = 480) -> tk.Label:
    """
    Create a tkinter widget for displaying screen preview
    
    Args:
        parent: Parent tkinter widget
        width: Preview width
        height: Preview height
        
    Returns:
        Label widget for displaying screen frames
    """
    preview_label = tk.Label(
        parent,
        width=width,
        height=height,
        bg="black",
        text="Screen Preview\n(Not capturing)",
        fg="white",
        font=("Arial", 12)
    )
    
    return preview_label