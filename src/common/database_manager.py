"""
Database Manager for FocusClass Tkinter Application
Handles SQLite operations for sessions, attendance, and violations
"""

import sqlite3
import aiosqlite
import asyncio
import datetime
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path


class DatabaseManager:
    """Manages SQLite database operations for the FocusClass application"""
    
    def __init__(self, db_path: str = "logs/focusclass.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    async def initialize_database(self):
        """Initialize database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Sessions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_code TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    teacher_ip TEXT NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    focus_mode BOOLEAN DEFAULT 0,
                    max_students INTEGER DEFAULT 200,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Students table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    student_name TEXT NOT NULL,
                    student_ip TEXT NOT NULL,
                    join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    leave_time TIMESTAMP,
                    status TEXT DEFAULT 'connected',
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            # Violations table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    student_id INTEGER,
                    violation_type TEXT NOT NULL,
                    description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    severity TEXT DEFAULT 'medium',
                    resolved BOOLEAN DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions (id),
                    FOREIGN KEY (student_id) REFERENCES students (id)
                )
            """)
            
            # Screen sharing requests table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS screen_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    student_id INTEGER,
                    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    approved BOOLEAN DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions (id),
                    FOREIGN KEY (student_id) REFERENCES students (id)
                )
            """)
            
            # Activity logs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    student_id INTEGER,
                    activity_type TEXT NOT NULL,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id),
                    FOREIGN KEY (student_id) REFERENCES students (id)
                )
            """)
            
            await db.commit()
            self.logger.info("Database initialized successfully")
    
    # Session Management
    async def create_session(self, session_code: str, password: str, teacher_ip: str, 
                           max_students: int = 200) -> int:
        """
        Create a new session
        
        Args:
            session_code: Unique session identifier
            password: Session password
            teacher_ip: Teacher's IP address
            max_students: Maximum number of students allowed
            
        Returns:
            Session ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO sessions (session_code, password, teacher_ip, max_students)
                VALUES (?, ?, ?, ?)
            """, (session_code, password, teacher_ip, max_students))
            
            session_id = cursor.lastrowid
            await db.commit()
            
            self.logger.info(f"Created session {session_code} with ID {session_id}")
            return session_id
    
    async def get_session(self, session_code: str) -> Optional[Dict[str, Any]]:
        """Get session by session code"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM sessions WHERE session_code = ?
            """, (session_code,))
            
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def end_session(self, session_id: int):
        """End a session"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions 
                SET end_time = CURRENT_TIMESTAMP, status = 'ended'
                WHERE id = ?
            """, (session_id,))
            
            await db.execute("""
                UPDATE students 
                SET leave_time = CURRENT_TIMESTAMP, status = 'disconnected'
                WHERE session_id = ? AND status = 'connected'
            """, (session_id,))
            
            await db.commit()
            self.logger.info(f"Ended session {session_id}")
    
    async def update_focus_mode(self, session_id: int, focus_mode: bool):
        """Update focus mode status for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions SET focus_mode = ? WHERE id = ?
            """, (focus_mode, session_id))
            await db.commit()
    
    # Student Management
    async def add_student(self, session_id: int, student_name: str, 
                         student_ip: str) -> int:
        """
        Add a student to a session
        
        Args:
            session_id: Session ID
            student_name: Student's name
            student_ip: Student's IP address
            
        Returns:
            Student ID
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO students (session_id, student_name, student_ip)
                VALUES (?, ?, ?)
            """, (session_id, student_name, student_ip))
            
            student_id = cursor.lastrowid
            await db.commit()
            
            self.logger.info(f"Added student {student_name} with ID {student_id}")
            return student_id
    
    async def update_student_status(self, student_id: int, status: str):
        """Update student status"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE students 
                SET status = ?, last_seen = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, student_id))
            await db.commit()
    
    async def remove_student(self, student_id: int):
        """Remove student from session"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE students 
                SET leave_time = CURRENT_TIMESTAMP, status = 'disconnected'
                WHERE id = ?
            """, (student_id,))
            await db.commit()
    
    async def get_session_students(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all students in a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM students 
                WHERE session_id = ? AND status = 'connected'
                ORDER BY join_time
            """, (session_id,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # Violation Management
    async def log_violation(self, session_id: int, student_id: int, 
                          violation_type: str, description: str = None, 
                          severity: str = "medium"):
        """
        Log a violation
        
        Args:
            session_id: Session ID
            student_id: Student ID
            violation_type: Type of violation (e.g., "alt_tab", "app_switch")
            description: Detailed description
            severity: Violation severity (low, medium, high)
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO violations 
                (session_id, student_id, violation_type, description, severity)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, student_id, violation_type, description, severity))
            await db.commit()
            
            self.logger.warning(f"Logged {severity} violation: {violation_type} "
                              f"for student {student_id}")
    
    async def get_session_violations(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all violations for a session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT v.*, s.student_name 
                FROM violations v
                JOIN students s ON v.student_id = s.id
                WHERE v.session_id = ?
                ORDER BY v.timestamp DESC
            """, (session_id,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_student_violations(self, student_id: int) -> List[Dict[str, Any]]:
        """Get all violations for a specific student"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM violations 
                WHERE student_id = ?
                ORDER BY timestamp DESC
            """, (student_id,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # Screen Request Management
    async def create_screen_request(self, session_id: int, student_id: int) -> int:
        """Create a screen sharing request"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO screen_requests (session_id, student_id)
                VALUES (?, ?)
            """, (session_id, student_id))
            
            request_id = cursor.lastrowid
            await db.commit()
            return request_id
    
    async def update_screen_request(self, request_id: int, approved: bool):
        """Update screen request status"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE screen_requests 
                SET response_time = CURRENT_TIMESTAMP, 
                    status = ?, approved = ?
                WHERE id = ?
            """, ("approved" if approved else "denied", approved, request_id))
            await db.commit()
    
    # Activity Logging
    async def log_activity(self, session_id: int, student_id: int, 
                          activity_type: str, details: str = None):
        """Log student activity"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO activity_logs 
                (session_id, student_id, activity_type, details)
                VALUES (?, ?, ?, ?)
            """, (session_id, student_id, activity_type, details))
            await db.commit()
    
    # Reporting and Analytics
    async def get_session_summary(self, session_id: int) -> Dict[str, Any]:
        """Get comprehensive session summary"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get session info
            session_cursor = await db.execute("""
                SELECT * FROM sessions WHERE id = ?
            """, (session_id,))
            session = await session_cursor.fetchone()
            
            # Get student count
            student_cursor = await db.execute("""
                SELECT COUNT(*) as total_students FROM students 
                WHERE session_id = ?
            """, (session_id,))
            student_count = await student_cursor.fetchone()
            
            # Get violation count
            violation_cursor = await db.execute("""
                SELECT COUNT(*) as total_violations FROM violations 
                WHERE session_id = ?
            """, (session_id,))
            violation_count = await violation_cursor.fetchone()
            
            # Get active students
            active_cursor = await db.execute("""
                SELECT COUNT(*) as active_students FROM students 
                WHERE session_id = ? AND status = 'connected'
            """, (session_id,))
            active_count = await active_cursor.fetchone()
            
            return {
                "session": dict(session) if session else None,
                "total_students": student_count["total_students"],
                "active_students": active_count["active_students"],
                "total_violations": violation_count["total_violations"]
            }
    
    async def export_session_data(self, session_id: int) -> Dict[str, Any]:
        """Export all session data for reporting"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get session data
            session_data = await self.get_session_summary(session_id)
            
            # Get all students
            students = await self.get_session_students(session_id)
            
            # Get all violations
            violations = await self.get_session_violations(session_id)
            
            # Get all activities
            activity_cursor = await db.execute("""
                SELECT a.*, s.student_name 
                FROM activity_logs a
                JOIN students s ON a.student_id = s.id
                WHERE a.session_id = ?
                ORDER BY a.timestamp
            """, (session_id,))
            activities = [dict(row) for row in await activity_cursor.fetchall()]
            
            return {
                "session_summary": session_data,
                "students": students,
                "violations": violations,
                "activities": activities,
                "export_timestamp": datetime.datetime.now().isoformat()
            }
    
    async def cleanup_old_sessions(self, days: int = 30):
        """Remove sessions older than specified days"""
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            
            await db.execute("""
                DELETE FROM sessions 
                WHERE created_at < ? AND status = 'ended'
            """, (cutoff_date,))
            
            await db.commit()
            self.logger.info(f"Cleaned up sessions older than {days} days")
    
    async def close(self):
        """Close database connections"""
        self.logger.info("Database manager closed")


# Utility functions for CSV/PDF export
def export_to_csv(data: Dict[str, Any], filename: str):
    """Export session data to CSV file"""
    import csv
    import os
    
    os.makedirs("exports", exist_ok=True)
    filepath = f"exports/{filename}"
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        if 'students' in data and data['students']:
            writer = csv.DictWriter(csvfile, fieldnames=data['students'][0].keys())
            writer.writeheader()
            writer.writerows(data['students'])
    
    return filepath


def export_to_pdf(data: Dict[str, Any], filename: str):
    """Export session data to PDF file (basic implementation)"""
    import os
    
    os.makedirs("exports", exist_ok=True)
    filepath = f"exports/{filename}"
    
    # This would require reportlab or similar library
    # For now, create a simple text file
    with open(filepath.replace('.pdf', '.txt'), 'w', encoding='utf-8') as f:
        f.write("FocusClass Session Report\n")
        f.write("=" * 30 + "\n\n")
        
        if 'session_summary' in data:
            session = data['session_summary']['session']
            if session:
                f.write(f"Session Code: {session['session_code']}\n")
                f.write(f"Start Time: {session['start_time']}\n")
                f.write(f"Total Students: {data['session_summary']['total_students']}\n")
                f.write(f"Total Violations: {data['session_summary']['total_violations']}\n\n")
        
        if 'violations' in data:
            f.write("Violations:\n")
            f.write("-" * 20 + "\n")
            for violation in data['violations']:
                f.write(f"Student: {violation['student_name']}\n")
                f.write(f"Type: {violation['violation_type']}\n")
                f.write(f"Time: {violation['timestamp']}\n")
                f.write(f"Severity: {violation['severity']}\n\n")
    
    return filepath.replace('.pdf', '.txt')