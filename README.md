# FocusClass Tkinter Edition 🎓

**A comprehensive classroom management system designed for digital learning environments.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)]()
[![GUI](https://img.shields.io/badge/GUI-Tkinter-orange.svg)]()

## 🌟 Features

### 👨‍🏫 **Teacher Features**
- **📊 Session Management**: Create and manage classroom sessions with unique codes
- **📱 QR Code Generation**: Easy student joining via QR codes
- **👥 Real-time Student Monitoring**: Track connected students and their activities
- **📺 Screen Sharing**: Share your screen with all students
- **🔒 Focus Mode**: Restrict student access to unauthorized applications
- **⚠️ Violation Tracking**: Monitor and log focus violations
- **📈 Session Analytics**: Detailed statistics and reporting
- **💾 Data Export**: Export session data for analysis

### 👨‍🎓 **Student Features**
- **🔗 Easy Connection**: Connect via IP, session code, and password
- **🖥️ Screen Sharing**: Share screen with teacher (with approval)
- **🔐 Focus Mode Compliance**: Automatic restriction enforcement
- **⚡ System Monitoring**: Battery, performance, and activity tracking
- **📝 Activity Logging**: Comprehensive activity and violation logs
- **🔄 Auto-reconnection**: Automatic reconnection on network issues

### 🛠️ **Technical Features**
- **🌐 LAN Communication**: WebSocket-based real-time communication
- **🗄️ SQLite Database**: Session data persistence and analytics
- **🎨 Responsive UI**: Modern, resizable tkinter interface
- **📋 Cross-platform**: Windows (full features), macOS, Linux (limited)
- **🔧 Easy Setup**: Automated dependency checking and installation
- **📊 Performance Monitoring**: Built-in performance tracking

## 🚀 Quick Start

### Windows (Recommended)
1. **Double-click `start.bat`** - This will handle everything automatically!
2. Choose your mode (Teacher or Student)
3. Start teaching! 🎉

### Manual Installation
1. **Install Python 3.8+** from [python.org](https://python.org)
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run setup check**:
   ```bash
   python setup_check.py
   ```
4. **Launch application**:
   ```bash
   python main.py
   ```

## Dependencies

- `tkinter` (built-in with Python)
- `websockets` - WebSocket communication
- `aiohttp` - HTTP server and client
- `mss` - Screen capture
- `Pillow` - Image processing
- `psutil` - System monitoring
- `qrcode` - QR code generation
- `aiosqlite` - Async SQLite operations

## Usage

### Starting the Application

1. Run `python main.py`
2. Choose between Teacher Mode or Student Mode

### Teacher Mode

1. **Start Session**
   - Click "📚 Start Session"
   - Session code and password will be generated
   - QR code will be displayed for easy student connectivity

2. **Screen Sharing**
   - Click "📺 Start Screen Sharing"
   - Select monitor and quality settings
   - Students will receive the shared screen

3. **Focus Mode**
   - Click "🔒 Enable Focus Mode"
   - Students will be restricted from switching applications
   - Violations will be logged and displayed

4. **Monitor Students**
   - View connected students in the Students tab
   - Monitor violations and activities in real-time
   - Export session data for reporting

### Student Mode

1. **Connect to Session**
   - Enter your name
   - Input teacher's IP address, session code, and password
   - OR scan QR code from teacher
   - Click "🔗 Connect"

2. **During Session**
   - View teacher's shared screen (when available)
   - System will monitor focus mode compliance
   - Activity logs show connection status and violations

## Network Configuration

### Teacher (Server)
- WebSocket Server: Port 8765
- HTTP Server: Port 8080
- Automatic IP detection and QR code generation

### Student (Client)
- Connects to teacher's IP address
- Automatic reconnection on connection loss
- Real-time communication for violations and activities

## Focus Mode Features

### Full Focus Mode (Administrator)
- Keyboard hook blocking (Alt+Tab, Windows key, etc.)
- Window switching prevention
- Task manager and system tool blocking
- Process monitoring for unauthorized applications

### Lightweight Focus Mode (Standard User)
- Window monitoring without system hooks
- Violation logging for unauthorized window focus
- Battery and system monitoring

## Production Ready Features

### Fixes from Original Version
✅ **Student IP Address Fixed** - Real IP addresses displayed instead of 127.0.0.1
✅ **Screen Selection Options** - Monitor and quality selection for screen sharing
✅ **Screen Sharing Transmission** - Fixed monitor selection and frame transmission
✅ **Violation Spam Prevention** - Intelligent throttling with 5-second cooldown
✅ **Enhanced Error Handling** - Comprehensive error handling and logging

### Additional Improvements
- Async/await pattern for non-blocking operations
- Memory-efficient violation throttling
- Real-time UI updates without blocking
- Cross-platform compatibility
- Modular architecture for easy maintenance

## File Structure

```
focusclass_tkinter/
├── main.py                 # Main launcher
├── src/
│   ├── common/            # Shared modules
│   │   ├── config.py      # Configuration settings
│   │   ├── utils.py       # Utility functions
│   │   ├── database_manager.py  # SQLite operations
│   │   ├── network_manager.py   # WebSocket communication
│   │   ├── screen_capture.py    # Screen capture functionality
│   │   └── focus_manager.py     # Focus mode enforcement
│   ├── teacher/           # Teacher application
│   │   └── teacher_app.py # Main teacher GUI
│   └── student/           # Student application
│       └── student_app.py # Main student GUI
├── assets/                # Static assets
├── logs/                  # Application logs
├── exports/               # Session data exports
└── requirements.txt       # Python dependencies
```

## Configuration

Configuration options can be modified in `src/common/config.py`:

- Network ports and timeouts
- Screen capture quality presets
- Focus mode settings
- UI theme and colors
- Database and logging configuration

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check network connectivity
   - Verify IP address and ports are accessible
   - Ensure firewall allows connections on ports 8765 and 8080

2. **Focus Mode Not Working**
   - Run as administrator for full functionality
   - Check Windows version compatibility
   - Verify no antivirus blocking system hooks

3. **Screen Sharing Issues**
   - Check screen capture permissions
   - Verify monitor selection is correct
   - Ensure sufficient network bandwidth

### Logging

Application logs are stored in the `logs/` directory:
- `launcher.log` - Main application startup
- `teacher.log` - Teacher application events
- `student.log` - Student application events

## Security Considerations

- Network communication is not encrypted (use VPN for sensitive environments)
- Focus mode requires system-level access on Windows
- Database contains session and activity data
- Screen sharing transmits visual data over network

## Comparison with PyQt5 Version

### Advantages of Tkinter Version
- ✅ Lighter weight and faster startup
- ✅ No external GUI library dependencies
- ✅ Better cross-platform compatibility
- ✅ Simpler deployment and installation
- ✅ More responsive UI updates

### Maintained Features
- ✅ All core functionality preserved
- ✅ Production-ready fixes included
- ✅ Same network protocol and database schema
- ✅ Compatible with existing session data
- ✅ Identical violation tracking and throttling

## License

This project is provided as-is for educational and classroom management purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review application logs
3. Verify system requirements and dependencies
4. Test network connectivity between teacher and students

## Version History

### v1.0.0 - Tkinter Edition
- Complete recreation using Tkinter
- All production fixes from PyQt5 version
- Enhanced async operation support
- Improved cross-platform compatibility
- Streamlined user interface