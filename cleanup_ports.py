#!/usr/bin/env python3
"""
Port Cleanup Utility for FocusClass
Helps clean up ports that might be in use by previous sessions
"""

import socket
import subprocess
import sys
import psutil
from typing import List


def get_process_using_port(port: int) -> List[dict]:
    """Get processes using a specific port"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'], 
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes


def is_port_in_use(port: int) -> bool:
    """Check if port is in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return False
    except socket.error:
        return True


def kill_process_by_pid(pid: int) -> bool:
    """Kill process by PID"""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=3)
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
        try:
            proc.kill()
            return True
        except:
            return False


def cleanup_focusclass_ports():
    """Clean up common FocusClass ports"""
    ports_to_check = [8765, 8080, 8766, 8081, 8082]
    
    print("FocusClass Port Cleanup Utility")
    print("=" * 40)
    
    for port in ports_to_check:
        print(f"\nChecking port {port}...")
        
        if not is_port_in_use(port):
            print(f"✓ Port {port} is available")
            continue
        
        print(f"⚠ Port {port} is in use")
        processes = get_process_using_port(port)
        
        if not processes:
            print(f"  Could not identify process using port {port}")
            continue
        
        for proc in processes:
            print(f"  Process: {proc['name']} (PID: {proc['pid']})")
            print(f"  Command: {proc['cmdline']}")
            
            # Check if it's likely a Python/FocusClass process
            if 'python' in proc['name'].lower() or 'focusclass' in proc['cmdline'].lower():
                try:
                    response = input(f"  Kill process {proc['pid']}? (y/n/a=all): ").lower()
                    if response in ['y', 'yes', 'a', 'all']:
                        if kill_process_by_pid(proc['pid']):
                            print(f"  ✓ Killed process {proc['pid']}")
                        else:
                            print(f"  ✗ Failed to kill process {proc['pid']}")
                        
                        if response in ['a', 'all']:
                            # Kill all remaining processes for this port
                            for remaining_proc in processes[processes.index(proc)+1:]:
                                if kill_process_by_pid(remaining_proc['pid']):
                                    print(f"  ✓ Killed process {remaining_proc['pid']}")
                                else:
                                    print(f"  ✗ Failed to kill process {remaining_proc['pid']}")
                            break
                    else:
                        print(f"  Skipping process {proc['pid']}")
                except KeyboardInterrupt:
                    print("\nCancelled by user")
                    return
            else:
                print(f"  Skipping non-Python process: {proc['name']}")
    
    print(f"\nPort cleanup completed!")
    
    # Verify ports are now free
    print("\nVerifying port availability...")
    for port in ports_to_check:
        if is_port_in_use(port):
            print(f"⚠ Port {port} still in use")
        else:
            print(f"✓ Port {port} is available")


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        # Auto mode - kill all Python processes using FocusClass ports
        ports_to_check = [8765, 8080]
        killed_any = False
        
        for port in ports_to_check:
            if is_port_in_use(port):
                processes = get_process_using_port(port)
                for proc in processes:
                    if 'python' in proc['name'].lower():
                        if kill_process_by_pid(proc['pid']):
                            print(f"Killed Python process {proc['pid']} using port {port}")
                            killed_any = True
        
        if not killed_any:
            print("No Python processes found using FocusClass ports")
    else:
        cleanup_focusclass_ports()


if __name__ == "__main__":
    main()