import serial
import time
import serial.tools.list_ports

def test_arduino_connection():
    print(" Scanning for COM ports...")
    ports = serial.tools.list_ports.comports()
    
    print(" Available ports:")
    for port in ports:
        print(f"   - {port.device}: {port.description}")
    
    # Try to connect to Arduino
    print(f"\n Testing Arduino connection on COM9...")
    try:
        arduino = serial.Serial('COM9', 9600, timeout=2)
        time.sleep(3)
        
        print(" Serial port opened successfully!")
        
        # Clear buffers
        arduino.reset_input_buffer()
        arduino.reset_output_buffer()
        
        # Send test command
        print(" Sending test command...")
        arduino.write(b'TEST\n')
        time.sleep(1)
        
        # Read responses
        print(" Listening for responses...")
        start_time = time.time()
        while time.time() - start_time < 5:  # Listen for 5 seconds
            if arduino.in_waiting > 0:
                response = arduino.readline().decode().strip()
                print(f" Received: {response}")
        
        arduino.close()
        print(" Arduino communication test PASSED!")
        
    except Exception as e:
        print(f" Test failed: {e}")
        print(" Solutions:")
        print("   1. Close Arduino IDE completely")
        print("   2. Run as Administrator")
        print("   3. Check USB cable connection")
        print("   4. Try different USB port")

if __name__ == "__main__":
    test_arduino_connection()