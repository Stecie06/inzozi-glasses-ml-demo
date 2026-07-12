import cv2
import time
import sys

def list_cameras():
    """List all available cameras"""
    print("🔍 Scanning for cameras...")
    
    # Check multiple camera indices
    for i in range(0, 5):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f" Camera {i}: WORKS - Frame: {frame.shape}")
            else:
                print(f" Camera {i}: Opens but no frame")
            cap.release()
        else:
            print(f" Camera {i}: Cannot open")
        
        time.sleep(0.5)

def test_camera_methods():
    """Test different camera methods"""
    print("\n Testing camera methods...")
    
    methods = [
        ("DirectShow Front", 0, cv2.CAP_DSHOW),
        ("DirectShow Back", 1, cv2.CAP_DSHOW), 
        ("Auto Front", 0, cv2.CAP_ANY),
        ("Auto Back", 1, cv2.CAP_ANY),
        ("MSMF Front", 0, cv2.CAP_MSMF),
        ("MSMF Back", 1, cv2.CAP_MSMF)
    ]
    
    for name, index, backend in methods:
        try:
            print(f" Testing {name}...")
            cap = cv2.VideoCapture(index, backend)
            
            # Try different resolutions
            resolutions = [(640, 480), (320, 240), (1280, 720), (800, 600)]
            
            for width, height in resolutions:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                time.sleep(0.5)
                
                ret, frame = cap.read()
                if ret and frame is not None:
                    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"   {width}x{height} -> Actual: {actual_width}x{actual_height} - Frame: {frame.shape}")
                    
                    # Test display
                    cv2.putText(frame, f"{name} - {actual_width}x{actual_height}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow(f'Camera Test - {name}', frame)
                    cv2.waitKey(1000)  # Show for 1 second
                    cv2.destroyAllWindows()
                    break
                else:
                    print(f"   {width}x{height} failed")
            
            cap.release()
            
        except Exception as e:
            print(f"   {name} error: {e}")

def main():
    print("📹 CAMERA DIAGNOSTIC TOOL")
    print("=" * 50)
    
    list_cameras()
    test_camera_methods()
    
    print("\n TROUBLESHOOTING TIPS:")
    print("1. Run as Administrator")
    print("2. Close all other camera apps (Zoom, Skype, etc.)")
    print("3. Check Windows Camera Privacy Settings")
    print("4. Try different USB ports")
    print("5. Update camera drivers")

if __name__ == "__main__":
    main()