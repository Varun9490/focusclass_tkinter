# FocusClass Quick Start Guide 🚀

## 📋 Pre-Installation Checklist

### System Requirements
- ✅ Windows 10/11 (recommended for full features)
- ✅ Python 3.8 or higher installed
- ✅ All devices on the same local network
- ✅ Administrator privileges (for focus mode)

### Network Preparation  
- 🔥 Disable firewall temporarily OR add exceptions for ports 8765 and 8080
- 🌐 Ensure all devices can ping each other
- 📡 Use wired connection for best performance

## 🎯 Quick Installation (Windows)

### Option 1: Automatic (Easiest)
1. Download FocusClass Tkinter folder
2. **Double-click `start.bat`**
3. Follow the prompts - it will install everything automatically!

### Option 2: Manual
1. Open Command Prompt or PowerShell
2. Navigate to the FocusClass folder:
   ```cmd
   cd "path\to\focusclass_tkinter"
   ```
3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
4. Run setup check:
   ```cmd
   python setup_check.py
   ```
5. Launch application:
   ```cmd
   python main.py
   ```

## 👨‍🏫 Teacher Setup (5 Minutes)

### Step 1: Start Teacher Mode
1. Run the application (double-click `start.bat` or `python main.py`)
2. Click **"👨‍🏫 Teacher Mode"**
3. Wait for the teacher interface to load

### Step 2: Create Session
1. Click **"📚 Start Session"**
2. 🎉 **Session is now active!**
3. Note down or share:
   - **Session Code** (8 characters)
   - **Password** (for security)
   - **Your IP Address** (displayed)
   - **QR Code** (easiest for students)

### Step 3: Configure Features
- 📺 **Screen Sharing**: Click "Start Screen Sharing" to share your screen
- 🔒 **Focus Mode**: Click "Enable Focus Mode" to restrict student access
- 👥 **Monitor Students**: Check the "Connected Students" tab

### Step 4: During Class
- 📊 Watch real-time statistics
- ⚠️ Monitor violations in "Activity Log"
- 📤 Export data when finished: "Statistics" → "Export Session Data"

## 👨‍🎓 Student Setup (2 Minutes)

### Step 1: Start Student Mode
1. Run the application on student computer
2. Click **"👨‍🎓 Student Mode"**

### Step 2: Connect to Teacher
**Option A: QR Code (Easiest)**
- Use phone camera or QR scanner app
- Scan teacher's QR code
- App will auto-fill connection details

**Option B: Manual Entry**
1. Enter your **Name**
2. Enter **Teacher IP** (get from teacher)
3. Enter **Session Code** (8 characters)
4. Enter **Password**
5. Click **"🔗 Connect"**

### Step 3: During Class
- ✅ Stay connected (green status)
- 🔋 Keep battery above 20%
- 🎯 Follow focus mode rules
- 📋 Check activity log for messages

## 🔧 Troubleshooting

### ❌ "Connection Failed" (Student)
1. **Check network**: Can you ping teacher's IP?
   ```cmd
   ping [teacher-ip]
   ```
2. **Verify details**: Double-check session code and password
3. **Firewall**: Teacher may need to allow ports 8765 and 8080
4. **Try again**: Click "Disconnect" then "Connect"

### ❌ "No Students Connecting" (Teacher)
1. **Check firewall**: Allow incoming connections
   ```cmd
   netsh advfirewall firewall add rule name="FocusClass" dir=in action=allow protocol=TCP localport=8765
   ```
2. **Share details clearly**: Ensure students have correct IP and session code
3. **Network issues**: All devices must be on same WiFi/LAN

### ❌ "Focus Mode Not Working"
1. **Run as Administrator**: Right-click → "Run as administrator"
2. **Windows version**: Requires Windows 10/11
3. **Antivirus**: May block system hooks - add exception
4. **Fallback**: Use lightweight mode (automatic fallback)

### ❌ "Screen Sharing Issues"
1. **Graphics drivers**: Update display drivers
2. **Monitor selection**: Choose correct monitor in settings
3. **Performance**: Reduce quality to "medium" or "low"
4. **Network**: Check bandwidth - screen sharing is data-intensive

### ❌ "Application Won't Start"
1. **Dependencies**: Run `python setup_check.py --install`
2. **Python version**: Verify `python --version` shows 3.8+
3. **Reinstall**: Delete and re-download application
4. **Logs**: Check `logs/launcher.log` for error details

## 💡 Pro Tips

### For Teachers
- 🖥️ **Dual Monitor**: Use secondary monitor for teaching materials
- 📊 **Quality Settings**: Use "medium" quality for 10+ students
- 🔄 **Session Management**: End session properly to save all data
- 📁 **Export Data**: Regular exports for attendance and behavior tracking

### For Students  
- 🔋 **Battery Management**: Keep devices charged
- 🌐 **Network Stability**: Use wired connection if possible
- 🚫 **App Switching**: Avoid switching apps during focus mode
- 📱 **Phone Away**: Keep phones away to avoid distractions

### For IT Administrators
- 🔥 **Firewall Rules**: Pre-configure firewall exceptions
- 📦 **Mass Deployment**: Use script to install on multiple machines
- 🔐 **Permissions**: Consider admin rights for focus mode features
- 📊 **Monitoring**: Set up centralized logging if needed

## 📞 Getting Help

### Before Asking for Help
1. ✅ Run `python setup_check.py --gui` for diagnostics
2. ✅ Check logs in `logs/` folder  
3. ✅ Try the troubleshooting steps above
4. ✅ Restart both teacher and student applications

### Common Solutions
- 🔄 **Restart**: Most issues resolved by restarting apps
- 🌐 **Network**: 90% of issues are network-related
- 🔧 **Dependencies**: Run setup check to verify installation
- 📋 **Logs**: Always check logs for specific error messages

## 🎉 Success Checklist

### Teacher Ready ✅
- [ ] Session started successfully
- [ ] QR code generated and visible
- [ ] IP address displayed correctly
- [ ] Screen sharing working (if enabled)
- [ ] Students can connect successfully

### Student Ready ✅
- [ ] Connected to teacher successfully
- [ ] Name appears in teacher's student list
- [ ] Can see teacher's screen (if shared)
- [ ] Focus mode restrictions working
- [ ] Activity log showing connection status

### Class Running Smoothly ✅
- [ ] All students connected and monitored
- [ ] Violation tracking working properly
- [ ] Screen sharing stable (if used)
- [ ] No network connectivity issues
- [ ] Session data being logged properly

---

**🎯 Remember**: FocusClass works best when all devices are on the same reliable network. Most issues are network-related, so ensure good connectivity before starting your session!

**🚀 Happy Teaching with FocusClass!** 📚✨