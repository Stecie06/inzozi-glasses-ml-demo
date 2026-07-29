#!/usr/bin/env python3
"""
Run Inzozi Smart Glasses with Web Interface
This runs your smart_glasses_phone_fixed.py alongside the web interface
"""

import os
import sys
import time
import threading
import subprocess
import webbrowser
import socket

def get_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def run_web_interface():
    """Run the smart glasses web interface"""
    try:
        print("🌐 Starting web interface...")
        # Import and run the glasses app
        import smart_glasses_app
        # The app runs in its own thread
        print("✅ Web interface running on port 5000")
    except Exception as e:
        print(f"⚠️ Could not run web interface: {e}")

def run_smart_glasses():
    """Run your smart_glasses_phone_fixed.py"""
    print("👓 Starting Smart Glasses system...")
    try:
        # Import your smart glasses system
        import smart_glasses_phone_fixed
        
        # Create an instance and run it
        # You can customize these parameters
        system = smart_glasses_phone_fixed.SmartGlassesWithML(
            phone_ip="192.168.2.102",  # Your phone IP
            arduino_port="COM12",       # Your Arduino port
            use_kinyarwanda=False,
            enable_object_detection=True,
            enable_emotion_detection=True
        )
        
        print("✅ Smart Glasses system initialized")
        print("📱 Starting camera and ML processing...")
        
        # Run the system (this will block)
        system.run()
        
    except Exception as e:
        print(f"❌ Error running smart glasses: {e}")
        import traceback
        traceback.print_exc()

def open_browser():
    """Open the browser after a delay"""
    time.sleep(3)
    ip = get_ip()
    url = f"http://{ip}:5000/glasses"
    print(f"\n🌐 Opening browser at: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" INZOZI SMART GLASSES - Complete System with Web Interface")
    print("=" * 70)
    print("\n📋 Options:")
    print("   1. Run smart glasses with web interface (both)")
    print("   2. Run only smart glasses (no web)")
    print("   3. Run only web interface (no glasses)")
    print("\n" + "=" * 70)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = input("Select option (1, 2, or 3): ").strip()
    
    if mode == "2":
        # Run only smart glasses
        print("\n👓 Running Smart Glasses only...")
        run_smart_glasses()
        
    elif mode == "3":
        # Run only web interface
        print("\n🌐 Running Web Interface only...")
        os.system("python smart_glasses_app.py")
        
    else:
        # Run both (default)
        print("\n🚀 Running Smart Glasses with Web Interface...")
        print("=" * 70)
        
        ip = get_ip()
        print(f"\n📱 Access the web interface on your phone:")
        print(f"   http://{ip}:5000/glasses")
        print(f"\n📱 Or on your computer:")
        print(f"   http://localhost:5000/glasses")
        print("\n" + "=" * 70 + "\n")
        
        # Start web interface in a separate thread
        web_thread = threading.Thread(target=run_web_interface, daemon=True)
        web_thread.start()
        
        # Wait for web server to start
        time.sleep(2)
        
        # Open browser
        open_browser()
        
        # Run smart glasses in the main thread
        print("\n👓 Starting Smart Glasses system...")
        print("   Press 'Q' to quit the glasses system")
        print("   The web interface will continue running\n")
        
        try:
            run_smart_glasses()
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)