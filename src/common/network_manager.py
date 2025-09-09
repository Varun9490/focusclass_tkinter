"""
Network Manager for FocusClass Tkinter Application
Handles LAN communication, WebSocket connections, and WebRTC streaming
"""

import asyncio
import json
import logging
import socket
import uuid
import secrets
from typing import Dict, List, Optional, Callable, Any
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol
import aiohttp
from aiohttp import web, WSMsgType
import ssl
import time

# Optional imports with fallbacks
try:
    from aiortc import RTCPeerConnection, RTCDataChannel, RTCSessionDescription
    from aiortc.contrib.media import MediaPlayer, MediaRelay
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    print("Warning: aiortc not available. WebRTC features will be disabled.")
    
    # Create dummy classes for compatibility
    class RTCPeerConnection:
        async def close(self): pass
        async def createOffer(self): return None
        async def createAnswer(self): return None
        async def setLocalDescription(self, desc): pass
        async def setRemoteDescription(self, desc): pass
        def addTrack(self, track): pass
    
    class RTCDataChannel:
        async def send(self, data): pass
    
    class RTCSessionDescription:
        def __init__(self, sdp, type): pass
    
    class MediaPlayer:
        def __init__(self, *args, **kwargs): pass
    
    class MediaRelay:
        def subscribe(self, track): return track

try:
    from zeroconf import ServiceInfo, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    print("Warning: zeroconf not available. Network discovery will be disabled.")
    
    # Create dummy classes for compatibility
    class ServiceInfo:
        def __init__(self, *args, **kwargs): pass
    
    class Zeroconf:
        def __init__(self): pass
        def register_service(self, info): pass
        def unregister_service(self, info): pass
        def close(self): pass


class NetworkManager:
    """Manages network communication for FocusClass application"""
    
    def __init__(self, is_teacher: bool = False):
        """
        Initialize network manager
        
        Args:
            is_teacher: Whether this is a teacher or student instance
        """
        self.is_teacher = is_teacher
        self.logger = logging.getLogger(__name__)
        
        # Connection management
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.data_channels: Dict[str, RTCDataChannel] = {}
        
        # Server components (teacher only)
        self.websocket_server = None
        self.http_server = None
        self.zeroconf = None
        self.service_info = None
        
        # Client components (student only)
        self.websocket_client = None
        self.peer_connection = None
        
        # Event handlers
        self.message_handlers: Dict[str, Callable] = {}
        self.connection_handlers: Dict[str, Callable] = {}
        
        # Media relay for WebRTC
        if WEBRTC_AVAILABLE:
            self.media_relay = MediaRelay()
        else:
            self.media_relay = None
        
        # Network configuration
        self.host = "0.0.0.0"
        self.websocket_port = 8765
        self.http_port = 8080
        self.stun_servers = ["stun:stun.l.google.com:19302"]
        
    def get_local_ip(self) -> str:
        """Get the local IP address"""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    def get_client_ip(self, client_id: str) -> str:
        """Get IP address of connected client"""
        connection_info = self.connections.get(client_id)
        if connection_info:
            return connection_info.get('ip_address', 'unknown')
        return 'unknown'
    
    def get_client_info(self, client_id: str) -> dict:
        """Get detailed information about connected client"""
        connection_info = self.connections.get(client_id)
        if connection_info:
            return {
                'client_id': client_id,
                'ip_address': connection_info.get('ip_address', 'unknown'),
                'connected_at': connection_info.get('connected_at', 0),
                'connected_duration': time.time() - connection_info.get('connected_at', 0)
            }
        return {'client_id': client_id, 'ip_address': 'unknown', 'connected_at': 0, 'connected_duration': 0}
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return True
        except socket.error:
            return False
    
    def _find_available_port(self, start_port: int, max_attempts: int = 100) -> Optional[int]:
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + max_attempts):
            if self._is_port_available(port):
                self.logger.info(f"Found available port: {port} (original: {start_port})")
                return port
        return None
    
    # Teacher Server Methods
    async def start_teacher_server(self, session_code: str, password: str) -> Dict[str, Any]:
        """
        Start teacher server with WebSocket and HTTP endpoints
        
        Args:
            session_code: Unique session identifier
            password: Session password
            
        Returns:
            Server information
        """
        if not self.is_teacher:
            raise ValueError("This method is only for teacher instances")
        
        self.session_code = session_code
        self.session_password = password
        
        # Check if ports are available and find alternatives if needed
        if not self._is_port_available(self.websocket_port):
            self.websocket_port = self._find_available_port(self.websocket_port)
            if not self.websocket_port:
                raise Exception("No available ports found for WebSocket server")
        
        if not self._is_port_available(self.http_port):
            self.http_port = self._find_available_port(self.http_port)
            if not self.http_port:
                raise Exception("No available ports found for HTTP server")
        
        # Start WebSocket server
        await self._start_websocket_server()
        
        # Start HTTP server for REST API
        await self._start_http_server()
        
        # Register service with Zeroconf for discovery
        await self._register_service()
        
        local_ip = self.get_local_ip()
        
        server_info = {
            "session_code": session_code,
            "password": password,
            "ip": local_ip,
            "websocket_port": self.websocket_port,
            "http_port": self.http_port,
            "discovery_name": f"FocusClass-{session_code}"
        }
        
        self.logger.info(f"Teacher server started: {server_info}")
        return server_info
    
    async def _start_websocket_server(self):
        """Start WebSocket server for real-time communication"""
        async def handle_websocket(websocket, path):
            client_id = str(uuid.uuid4())
            
            # Get real client IP address
            try:
                # Extract client IP from websocket remote address
                if hasattr(websocket, 'remote_address'):
                    client_ip = websocket.remote_address[0]
                elif hasattr(websocket, 'transport') and hasattr(websocket.transport, 'get_extra_info'):
                    peername = websocket.transport.get_extra_info('peername')
                    client_ip = peername[0] if peername else "unknown"
                else:
                    client_ip = "unknown"
            except Exception as e:
                self.logger.warning(f"Could not get client IP: {e}")
                client_ip = "unknown"
            
            self.connections[client_id] = {
                'websocket': websocket,
                'ip_address': client_ip,
                'connected_at': time.time()
            }
            
            try:
                self.logger.info(f"New WebSocket connection: {client_id} from {client_ip}")
                
                # Send welcome message
                await self._send_message(client_id, "welcome", {
                    "client_id": client_id,
                    "session_code": self.session_code,
                    "server_time": time.time()
                })
                
                # Handle connection event
                if "connection" in self.connection_handlers:
                    await self.connection_handlers["connection"](client_id, websocket)
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await self._handle_message(client_id, data)
                    except json.JSONDecodeError:
                        self.logger.error(f"Invalid JSON from {client_id}: {message}")
                    except Exception as e:
                        self.logger.error(f"Error handling message from {client_id}: {e}")
            
            except websockets.exceptions.ConnectionClosed:
                self.logger.info(f"WebSocket connection closed: {client_id} ({client_ip})")
            except Exception as e:
                self.logger.error(f"WebSocket error for {client_id}: {e}")
            finally:
                # Clean up connection
                if client_id in self.connections:
                    del self.connections[client_id]
                if client_id in self.peer_connections:
                    await self.peer_connections[client_id].close()
                    del self.peer_connections[client_id]
                if client_id in self.data_channels:
                    del self.data_channels[client_id]
                
                # Handle disconnection event
                if "disconnection" in self.connection_handlers:
                    await self.connection_handlers["disconnection"](client_id)
        
        self.websocket_server = await websockets.serve(
            handle_websocket, 
            self.host, 
            self.websocket_port
        )
        
        self.logger.info(f"WebSocket server started on {self.host}:{self.websocket_port}")
    
    async def _start_http_server(self):
        """Start HTTP server for REST API and file serving"""
        app = web.Application()
        
        # REST API routes
        app.router.add_post('/api/join', self._handle_join_request)
        app.router.add_get('/api/session/{session_code}', self._handle_session_info)
        app.router.add_post('/api/screen_request', self._handle_screen_request)
        
        # Static file serving (for QR codes, etc.)
        app.router.add_static('/', path='assets', name='static')
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.http_port)
        await site.start()
        
        self.http_server = runner
        self.logger.info(f"HTTP server started on {self.host}:{self.http_port}")
    
    async def _register_service(self):
        """Register service with Zeroconf for LAN discovery"""
        if not ZEROCONF_AVAILABLE:
            self.logger.warning("Zeroconf not available. Network discovery disabled.")
            return
            
        try:
            local_ip = self.get_local_ip()
            
            # Service type for FocusClass
            service_type = "_focusclass._tcp.local."
            service_name = f"FocusClass-{self.session_code}.{service_type}"
            
            # Service properties
            properties = {
                b"session_code": self.session_code.encode(),
                b"version": b"1.0.0",
                b"ws_port": str(self.websocket_port).encode(),
                b"http_port": str(self.http_port).encode()
            }
            
            self.service_info = ServiceInfo(
                service_type,
                service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self.websocket_port,
                properties=properties
            )
            
            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.service_info)
            
            self.logger.info(f"Service registered: {service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to register service: {e}")
    
    # HTTP API Handlers
    async def _handle_join_request(self, request):
        """Handle student join request"""
        try:
            data = await request.json()
            student_name = data.get("student_name")
            password = data.get("password")
            
            if password != self.session_password:
                return web.json_response({
                    "success": False,
                    "error": "Invalid password"
                }, status=401)
            
            # Validate session capacity
            if len(self.connections) >= 200:  # Max students
                return web.json_response({
                    "success": False,
                    "error": "Session is full"
                }, status=429)
            
            # Handle join request
            if "join_request" in self.message_handlers:
                result = await self.message_handlers["join_request"](data)
                return web.json_response(result)
            
            return web.json_response({
                "success": True,
                "message": "Join request accepted",
                "websocket_port": self.websocket_port
            })
            
        except Exception as e:
            self.logger.error(f"Error handling join request: {e}")
            return web.json_response({
                "success": False,
                "error": "Internal server error"
            }, status=500)
    
    async def _handle_session_info(self, request):
        """Handle session info request"""
        session_code = request.match_info['session_code']
        
        if session_code != self.session_code:
            return web.json_response({
                "success": False,
                "error": "Session not found"
            }, status=404)
        
        return web.json_response({
            "success": True,
            "session_code": self.session_code,
            "websocket_port": self.websocket_port,
            "connected_students": len(self.connections),
            "max_students": 200
        })
    
    async def _handle_screen_request(self, request):
        """Handle screen sharing request"""
        try:
            data = await request.json()
            
            if "screen_request" in self.message_handlers:
                result = await self.message_handlers["screen_request"](data)
                return web.json_response(result)
            
            return web.json_response({
                "success": True,
                "message": "Screen request processed"
            })
            
        except Exception as e:
            self.logger.error(f"Error handling screen request: {e}")
            return web.json_response({
                "success": False,
                "error": "Internal server error"
            }, status=500)
    
    # Student Client Methods
    async def connect_to_teacher(self, teacher_ip: str, session_code: str, 
                               password: str, student_name: str) -> bool:
        """
        Connect student to teacher server
        
        Args:
            teacher_ip: Teacher's IP address
            session_code: Session code
            password: Session password
            student_name: Student's name
            
        Returns:
            Connection success status
        """
        if self.is_teacher:
            raise ValueError("This method is only for student instances")
        
        try:
            # First, authenticate via HTTP API
            join_url = f"http://{teacher_ip}:{self.http_port}/api/join"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(join_url, json={
                    "student_name": student_name,
                    "password": password,
                    "session_code": session_code
                }) as response:
                    if response.status != 200:
                        result = await response.json()
                        self.logger.error(f"Join request failed: {result.get('error')}")
                        return False
            
            # Connect via WebSocket
            ws_url = f"ws://{teacher_ip}:{self.websocket_port}"
            self.websocket_client = await websockets.connect(ws_url)
            
            # Send authentication
            await self.websocket_client.send(json.dumps({
                "type": "authenticate",
                "data": {
                    "student_name": student_name,
                    "password": password,
                    "session_code": session_code
                }
            }))
            
            # Start message handling
            asyncio.create_task(self._handle_client_messages())
            
            self.logger.info(f"Connected to teacher at {teacher_ip}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to teacher: {e}")
            return False
    
    async def _handle_client_messages(self):
        """Handle incoming messages from teacher (student side)"""
        try:
            async for message in self.websocket_client:
                try:
                    data = json.loads(message)
                    await self._handle_message("teacher", data)
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON from teacher: {message}")
                except Exception as e:
                    self.logger.error(f"Error handling teacher message: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Connection to teacher closed")
            if "disconnection" in self.connection_handlers:
                await self.connection_handlers["disconnection"]("teacher")
        except Exception as e:
            self.logger.error(f"Client message handling error: {e}")
    
    # WebRTC Methods
    async def create_peer_connection(self, client_id: str) -> RTCPeerConnection:
        """Create WebRTC peer connection"""
        if not WEBRTC_AVAILABLE:
            self.logger.warning("WebRTC not available. Returning dummy peer connection.")
            return RTCPeerConnection()
            
        pc = RTCPeerConnection(configuration={
            "iceServers": [{"urls": self.stun_servers}]
        })
        
        self.peer_connections[client_id] = pc
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            self.logger.info(f"Connection state for {client_id}: {pc.connectionState}")
        
        @pc.on("datachannel")
        def on_datachannel(channel):
            self.logger.info(f"Data channel created for {client_id}: {channel.label}")
            self.data_channels[f"{client_id}_{channel.label}"] = channel
            
            @channel.on("message")
            def on_message(message):
                asyncio.create_task(self._handle_datachannel_message(
                    client_id, channel.label, message
                ))
        
        return pc
    
    async def create_offer(self, client_id: str, media_track=None) -> dict:
        """Create WebRTC offer"""
        if not WEBRTC_AVAILABLE:
            self.logger.warning("WebRTC not available. Returning dummy offer.")
            return {"type": "offer", "sdp": "dummy"}
            
        pc = await self.create_peer_connection(client_id)
        
        if media_track:
            pc.addTrack(media_track)
        
        # Create data channel for control messages
        channel = pc.createDataChannel("control")
        self.data_channels[f"{client_id}_control"] = channel
        
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        return {
            "type": offer.type,
            "sdp": offer.sdp
        }
    
    async def handle_answer(self, client_id: str, answer: dict):
        """Handle WebRTC answer"""
        if not WEBRTC_AVAILABLE:
            self.logger.warning("WebRTC not available. Ignoring answer.")
            return
            
        pc = self.peer_connections.get(client_id)
        if pc:
            await pc.setRemoteDescription(RTCSessionDescription(
                sdp=answer["sdp"],
                type=answer["type"]
            ))
    
    async def handle_ice_candidate(self, client_id: str, candidate: dict):
        """Handle ICE candidate"""
        if not WEBRTC_AVAILABLE:
            self.logger.warning("WebRTC not available. Ignoring ICE candidate.")
            return
            
        pc = self.peer_connections.get(client_id)
        if pc and candidate.get("candidate"):
            await pc.addIceCandidate(candidate)
    
    async def _handle_datachannel_message(self, client_id: str, channel_label: str, message: str):
        """Handle message from WebRTC data channel"""
        try:
            data = json.loads(message)
            self.logger.debug(f"Data channel message from {client_id}:{channel_label}: {data}")
            
            # Handle control messages
            if channel_label == "control":
                await self._handle_message(client_id, data)
                
        except Exception as e:
            self.logger.error(f"Error handling data channel message: {e}")
    
    # Message Handling
    async def _handle_message(self, client_id: str, data: dict):
        """Handle incoming message"""
        message_type = data.get("type")
        message_data = data.get("data", {})
        
        self.logger.debug(f"Message from {client_id}: {message_type}")
        
        # Handle authentication specially for teacher
        if message_type == "authenticate" and self.is_teacher:
            await self._handle_authentication(client_id, message_data)
            return
        
        if message_type in self.message_handlers:
            try:
                await self.message_handlers[message_type](client_id, message_data)
            except Exception as e:
                self.logger.error(f"Error in message handler {message_type}: {e}")
        else:
            self.logger.warning(f"No handler for message type: {message_type}")
    
    async def _handle_authentication(self, client_id: str, data: dict):
        """Handle student authentication"""
        try:
            student_name = data.get("student_name")
            password = data.get("password")
            session_code = data.get("session_code")
            
            # Validate credentials
            if password == self.session_password and session_code == self.session_code:
                # Authentication successful
                await self._send_message(client_id, "auth_success", {
                    "message": "Authentication successful",
                    "student_name": student_name,
                    "session_code": session_code
                })
                
                # Notify application layer
                if "authenticate" in self.message_handlers:
                    await self.message_handlers["authenticate"](client_id, data)
                    
            else:
                # Authentication failed
                await self._send_message(client_id, "auth_failed", {
                    "reason": "Invalid credentials"
                })
                
                # Close connection
                connection_info = self.connections.get(client_id)
                if connection_info:
                    websocket = connection_info.get('websocket')
                    if websocket:
                        await websocket.close()
                    
        except Exception as e:
            self.logger.error(f"Authentication error for {client_id}: {e}")
    
    async def _send_message(self, client_id: str, message_type: str, data: dict):
        """Send message to specific client"""
        message = {
            "type": message_type,
            "data": data,
            "timestamp": time.time()
        }
        
        try:
            if self.is_teacher:
                # Teacher sending to student
                connection_info = self.connections.get(client_id)
                if connection_info:
                    websocket = connection_info.get('websocket')
                    if websocket:
                        await websocket.send(json.dumps(message))
                    else:
                        self.logger.warning(f"No WebSocket for {client_id}")
                else:
                    self.logger.warning(f"No connection info for {client_id}")
            else:
                # Student sending to teacher
                if self.websocket_client:
                    await self.websocket_client.send(json.dumps(message))
                else:
                    self.logger.warning("No WebSocket connection to teacher")
                    
        except Exception as e:
            self.logger.error(f"Error sending message to {client_id}: {e}")
    
    async def broadcast_message(self, message_type: str, data: dict, exclude: List[str] = None):
        """Broadcast message to all connected clients"""
        if not self.is_teacher:
            raise ValueError("Broadcasting is only available for teacher instances")
        
        exclude = exclude or []
        message = {
            "type": message_type,
            "data": data,
            "timestamp": time.time()
        }
        
        disconnected_clients = []
        
        for client_id, connection_info in self.connections.items():
            if client_id not in exclude:
                try:
                    websocket = connection_info.get('websocket')
                    if websocket:
                        await websocket.send(json.dumps(message))
                    else:
                        disconnected_clients.append(client_id)
                except Exception as e:
                    self.logger.error(f"Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            if client_id in self.connections:
                del self.connections[client_id]
    
    # Service Discovery
    async def discover_teachers(self, timeout: int = 5) -> List[Dict[str, Any]]:
        """Discover available teacher sessions on LAN"""
        if self.is_teacher:
            raise ValueError("Discovery is only for student instances")
        
        if not ZEROCONF_AVAILABLE:
            self.logger.warning("Zeroconf not available. Service discovery disabled.")
            return []
        
        discovered_services = []
        
        try:
            from zeroconf import ServiceBrowser, ServiceListener
            
            class DiscoveryListener(ServiceListener):
                def __init__(self):
                    self.services = []
                
                def remove_service(self, zeroconf, type, name):
                    pass
                
                def add_service(self, zeroconf, type, name):
                    info = zeroconf.get_service_info(type, name)
                    if info:
                        service_data = {
                            "name": name,
                            "address": socket.inet_ntoa(info.addresses[0]),
                            "port": info.port,
                            "properties": {
                                k.decode(): v.decode() 
                                for k, v in info.properties.items()
                            }
                        }
                        self.services.append(service_data)
            
            zeroconf = Zeroconf()
            listener = DiscoveryListener()
            browser = ServiceBrowser(zeroconf, "_focusclass._tcp.local.", listener)
            
            # Wait for discovery
            await asyncio.sleep(timeout)
            
            browser.cancel()
            zeroconf.close()
            
            discovered_services = listener.services
            
        except Exception as e:
            self.logger.error(f"Service discovery error: {e}")
        
        return discovered_services
    
    # Event Handler Registration
    def register_message_handler(self, message_type: str, handler: Callable):
        """Register message handler"""
        self.message_handlers[message_type] = handler
        self.logger.debug(f"Registered handler for message type: {message_type}")
    
    def register_connection_handler(self, event_type: str, handler: Callable):
        """Register connection event handler"""
        self.connection_handlers[event_type] = handler
        self.logger.debug(f"Registered handler for connection event: {event_type}")
    
    # Cleanup
    async def stop_server(self):
        """Stop teacher server"""
        if not self.is_teacher:
            return
        
        try:
            # Close all WebSocket connections first
            disconnect_tasks = []
            for client_id, connection_info in list(self.connections.items()):
                websocket = connection_info.get('websocket')
                if websocket:
                    try:
                        await websocket.close()
                    except Exception as e:
                        self.logger.warning(f"Error closing WebSocket for {client_id}: {e}")
            
            # Clear connections
            self.connections.clear()
            
            # Close all peer connections
            for pc in self.peer_connections.values():
                try:
                    await pc.close()
                except Exception as e:
                    self.logger.warning(f"Error closing peer connection: {e}")
            self.peer_connections.clear()
            self.data_channels.clear()
            
            # Close WebSocket server
            if self.websocket_server:
                self.websocket_server.close()
                try:
                    await self.websocket_server.wait_closed()
                except Exception as e:
                    self.logger.warning(f"Error waiting for WebSocket server closure: {e}")
                self.websocket_server = None
            
            # Stop HTTP server
            if self.http_server:
                try:
                    await self.http_server.cleanup()
                except Exception as e:
                    self.logger.warning(f"Error stopping HTTP server: {e}")
                self.http_server = None
            
            # Unregister service
            if ZEROCONF_AVAILABLE and self.zeroconf and self.service_info:
                try:
                    self.zeroconf.unregister_service(self.service_info)
                    self.zeroconf.close()
                except Exception as e:
                    self.logger.warning(f"Error unregistering service: {e}")
                self.zeroconf = None
                self.service_info = None
            
            self.logger.info("Teacher server stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping server: {e}")
    
    async def disconnect_client(self):
        """Disconnect student client"""
        if self.is_teacher:
            return
        
        try:
            if self.peer_connection:
                await self.peer_connection.close()
            
            if self.websocket_client:
                await self.websocket_client.close()
            
            self.logger.info("Disconnected from teacher")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")


# Utility functions
def generate_session_code() -> str:
    """Generate random session code"""
    return secrets.token_urlsafe(8).upper()


def generate_session_password() -> str:
    """Generate random session password"""
    return secrets.token_urlsafe(12)


def create_qr_code_data(teacher_ip: str, session_code: str, password: str) -> dict:
    """Create QR code data for easy joining"""
    return {
        "type": "focusclass_session",
        "teacher_ip": teacher_ip,
        "session_code": session_code,
        "password": password,
        "version": "1.0.0"
    }