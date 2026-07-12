import subprocess
import time
import os

def kill_com_port_processes(port='COM9'):
    """Kill all processes using the specified COM port"""
    print(f"🔧 Fixing COM port {port}...")
    
    try:
        # Find processes using the COM port
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=10)
        lines = result.stdout.split('\n')
        
        pids_to_kill = []
        for line in lines:
            if port in line:
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[4]
                    if pid.isdigit():
                        pids_to_kill.append(pid)
                        print(f"🛑 Found process PID {pid} using {port}")
        
        # Kill the processes
        for pid in set(pids_to_kill):
            try:
                print(f"💀 Killing process PID {pid}...")
                subprocess.run(['taskkill', '/pid', pid, '/f'], 
                             capture_output=True, timeout=5)
                time.sleep(1)
            except Exception as e:
                print(f" Could not kill PID {pid}: {e}")
        
        print(f" COM port {port} should be free now")
        return True
        
    except Exception as e:
        print(f" Error clearing COM port: {e}")
        return False

def check_arduino_ide_running():
    """Check if Arduino IDE is running"""
    try:
        result = subprocess.run(['tasklist', '/fi', 'imagename eq arduino.exe'], 
                              capture_output=True, text=True)
        if 'arduino.exe' in result.stdout:
            print(" Arduino IDE is running! Please close it completely.")
            return True
        else:
            print(" Arduino IDE is not running")
            return False
    except:
        return False

if __name__ == "__main__":
    print(" COM Port Fixer for Smart Glasses")
    print("="*50)
    
    # Check Arduino IDE
    check_arduino_ide_running()
    
    # Kill processes using COM9
    kill_com_port_processes('COM9')
    
    print("\n NEXT STEPS:")
    print("1. Close Arduino IDE completely")
    print("2. Disconnect and reconnect Arduino USB")
    print("3. Try a different USB port")
    print("4. Run the main system again")
    print("="*50)