#!/usr/bin/env python3
"""
SMART GLASSES - FIXED VERSION
No errors, smooth operation, reliable face recognition
"""

import cv2
import face_recognition
import numpy as np
import time
import os
import sys
import subprocess
import requests

# Try to import serial for Arduino (optional)
try:
    import serial
    ARDUINO_AVAILABLE = True
except ImportError:
    ARDUINO_AVAILABLE = False
    print(" pyserial not installed. Run: pip install pyserial")

class PhoneCamera:
    """Handles phone camera connection via IP Webcam"""
    def __init__(self, ip_address="10.187.14.132", port=8080):
        self.ip_address = ip_address
        self.port = port
        self.video_url = f"http://{ip_address}:{port}/video"
        self.cap = None
        
    def connect(self):
        """Connect to phone camera"""
        print(f" Connecting to phone camera at {self.video_url}...")
        
        try:
            test_url = f"http://{self.ip_address}:{self.port}"
            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                print(" IP Webcam server is running")
            else:
                print(f" Server responded with status: {response.status_code}")
                return False
        except Exception as e:
            print(f" Cannot reach phone: {e}")
            return False
        
        self.cap = cv2.VideoCapture(self.video_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                print(f" Connected successfully!")
                print(f"    Frame size: {frame.shape[1]}x{frame.shape[0]}")
                return True
            else:
                print(" Can open but cannot read frames")
                self.cap.release()
        else:
            print(" Cannot open video stream")
        
        return False
    
    def read(self):
        """Read frame from phone camera"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return True, frame
        return False, None
    
    def release(self):
        """Release camera"""
        if self.cap:
            self.cap.release()

class VoiceEngine:
    """Handles text-to-speech output"""
    def __init__(self):
        self.voice_enabled = True
        self.last_speech_by_type = {}
        self.use_kinyarwanda = True  # Set to False for English
        
    def speak(self, text, speech_type="general", cooldown=3):
        """Speak text using Windows voice with per-type cooldown"""
        if not self.voice_enabled:
            return
            
        current_time = time.time()
        
        if speech_type in self.last_speech_by_type:
            if current_time - self.last_speech_by_type[speech_type] < cooldown:
                return
        
        print(f" SPEAKING: {text}")
        self.last_speech_by_type[speech_type] = current_time
        
        try:
            escaped_text = text.replace('"', '`"')
            command = f'powershell -Command "Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak(\\\"{escaped_text}\\\")"'
            subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f" Voice error: {e}")

class ArduinoInterface:
    """Handles Arduino communication"""
    def __init__(self, port='COM9'):
        self.port = port
        self.arduino = None
        self.connected = False
        self.current_distance = -1
        
    def connect(self):
        if not ARDUINO_AVAILABLE:
            print(" Arduino not available (pyserial not installed)")
            return False
            
        try:
            print(f" Connecting to Arduino on {self.port}...")
            self.arduino = serial.Serial(port=self.port, baudrate=9600, timeout=1)
            time.sleep(2)
            self.arduino.reset_input_buffer()
            
            start_time = time.time()
            while time.time() - start_time < 5:
                if self.arduino.in_waiting:
                    line = self.arduino.readline().decode('utf-8').strip()
                    if line and "ARDUINO_READY" in line:
                        self.connected = True
                        print(" Arduino connected successfully!")
                        return True
                time.sleep(0.1)
            
            print(" Arduino connected but no ready signal")
            self.connected = True
            return True
            
        except Exception as e:
            print(f" Arduino connection failed: {e}")
            return False
    
    def read(self):
        if not self.connected or not self.arduino:
            return None
        try:
            if self.arduino.in_waiting:
                line = self.arduino.readline().decode('utf-8').strip()
                return line
        except:
            pass
        return None
    
    def process_message(self, message):
        if not message:
            return
        if message.startswith("DISTANCE:"):
            try:
                self.current_distance = int(message.split(":")[1])
            except:
                pass
    
    def close(self):
        if self.arduino and self.arduino.is_open:
            self.arduino.close()

class SmartGlassesPhone:
    """Smart Glasses - FIXED VERSION"""
    def __init__(self, arduino_port='COM9', phone_ip="192.168.1.69"):
        print("=" * 70)
        print(" SMART GLASSES - FIXED VERSION")
        print("=" * 70)
        
        # Initialize components
        self.voice = VoiceEngine()
        self.arduino = ArduinoInterface(arduino_port)
        self.phone_camera = PhoneCamera(phone_ip)
        
        # Face recognition
        self.known_face_encodings = []
        self.known_face_names = []
        self.last_detected_faces = {}
        self.frame_count = 0
        self.running = False
        
        # Load OpenCV face detector - ONLY ONE WE'LL USE
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Track if we're currently detecting faces
        self.faces_detected = False
        
        # Load faces
        self.load_known_faces()
        
        # Connect devices
        phone_connected = self.phone_camera.connect()
        arduino_connected = self.arduino.connect()
        
        print("\n SYSTEM STATUS:")
        print(f"   Phone Camera: {' CONNECTED' if phone_connected else '❌ NOT CONNECTED'}")
        print(f"   Arduino: {' CONNECTED' if arduino_connected else '❌ NOT CONNECTED'}")
        print(f"   Voice Output:  ENABLED")
        print(f"   Known Faces: {len(self.known_face_encodings)}")
        if self.known_face_names:
            print(f"   Names: {', '.join(self.known_face_names)}")
        print("=" * 70)
        
        if phone_connected and self.known_face_names:
            if self.voice.use_kinyarwanda:
                self.voice.speak(f"Sisitemu iteguye. Nshobora kumenya abantu {len(self.known_face_names)}", "startup", 0)
            else:
                self.voice.speak(f"System ready. I can recognize {len(self.known_face_names)} people", "startup", 0)
        else:
            if self.voice.use_kinyarwanda:
                self.voice.speak("Sisitemu iteguye", "startup", 0)
            else:
                self.voice.speak("System ready", "startup", 0)
    
    def load_known_faces(self):
        """Load known faces from directory"""
        faces_folder = "known_faces"
        
        if not os.path.exists(faces_folder):
            os.makedirs(faces_folder)
            print(" Created 'known_faces' folder")
            return
        
        self.known_face_encodings = []
        self.known_face_names = []
        
        face_files = [f for f in os.listdir(faces_folder) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
        
        if not face_files:
            print(" No face images found in 'known_faces' folder")
            return
        
        print(f" Loading {len(face_files)} face images...")
        
        for filename in face_files:
            try:
                image_path = os.path.join(faces_folder, filename)
                print(f"   Loading {filename}...")
                
                image = face_recognition.load_image_file(image_path)
                face_encodings = face_recognition.face_encodings(image)
                
                if face_encodings:
                    self.known_face_encodings.append(face_encodings[0])
                    person_name = os.path.splitext(filename)[0]
                    self.known_face_names.append(person_name)
                    print(f"    Loaded: {person_name}")
                else:
                    print(f"    No face found in: {filename}")
                    
            except Exception as e:
                print(f"    Error loading {filename}: {e}")
        
        print(f"📊 Successfully loaded {len(self.known_face_names)} known faces")
    
    def detect_faces_opencv_only(self, frame):
        """Use ONLY OpenCV - most reliable, no memory errors"""
        try:
            # Convert to grayscale for OpenCV
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces with optimized parameters
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60),  # Larger minimum size for better quality
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            # Convert to face_recognition format (top, right, bottom, left)
            face_locations = []
            for (x, y, w, h) in faces:
                face_locations.append((y, x + w, y + h, x))
            
            return face_locations
            
        except Exception as e:
            print(f" Face detection error: {e}")
            return []
    
    def recognize_and_speak_faces(self, frame):
        """Face recognition - FIXED VERSION"""
        try:
            self.frame_count += 1
            
            # Process EVERY frame for better detection
            # if self.frame_count % 2 != 0:
            #     return []
            
            # Use ONLY OpenCV detection (no CNN, no memory errors)
            face_locations = self.detect_faces_opencv_only(frame)
            
            if not face_locations:
                self.faces_detected = False
                return []
            
            # Get face encodings for recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize frame for faster processing
            small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
            small_face_locations = [
                (int(top*0.5), int(right*0.5), int(bottom*0.5), int(left*0.5))
                for (top, right, bottom, left) in face_locations
            ]
            
            try:
                face_encodings = face_recognition.face_encodings(small_frame, small_face_locations)
            except Exception as e:
                print(f" Encoding error: {e}")
                return []
            
            detected_faces = []
            current_time = time.time()
            
            for i, (face_location, face_encoding) in enumerate(zip(face_locations, face_encodings)):
                top, right, bottom, left = face_location
                
                name = "Unknown Person"
                confidence = 0.0
                best_distance = 1.0
                
                if self.known_face_encodings:
                    # Compare with known faces
                    face_distances = face_recognition.face_distance(
                        self.known_face_encodings, 
                        face_encoding
                    )
                    
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        best_distance = face_distances[best_match_index]
                        best_match_name = self.known_face_names[best_match_index]
                        confidence = max(0, 1 - best_distance)
                        
                        # Print ALL matches to debug
                        print(f"    Face {i+1}: {best_match_name} = {best_distance:.3f}")
                        
                        # Lenient threshold for phone camera (different from laptop)
                        if best_distance < 0.75:  # Phone cameras need higher threshold
                            name = best_match_name
                            self.faces_detected = True
                            print(f"    MATCH! {name} (distance: {best_distance:.3f})")
                            
                            # SPEAK THE NAME WITH DISTANCE
                            speech_key = f"face_{name}"
                            
                            if speech_key not in self.last_detected_faces or \
                               current_time - self.last_detected_faces[speech_key] > 8:
                                
                                # Get current distance from Arduino
                                distance = self.arduino.current_distance
                                
                                # Create announcement in Kinyarwanda or English
                                if self.voice.use_kinyarwanda:
                                    if distance > 0 and distance < 200:
                                        announcement = f"{name} ari kure ya santimetero {distance}"
                                    else:
                                        announcement = f"{name} nabonye"
                                else:
                                    if distance > 0 and distance < 200:
                                        announcement = f"{name} is {distance} centimeters away"
                                    else:
                                        announcement = f"{name} detected"
                                
                                self.voice.speak(announcement, speech_key, cooldown=8)
                                self.last_detected_faces[speech_key] = current_time
                
                detected_faces.append({
                    'location': (top, right, bottom, left),
                    'name': name,
                    'confidence': confidence,
                    'distance': best_distance
                })
            
            return detected_faces
            
        except Exception as e:
            print(f" Recognition error: {e}")
            self.faces_detected = False
            return []
    
    def speak_distance_alerts(self):
        """Distance-based obstacle alerts - ONLY WHEN NO FACES ARE DETECTED"""
        if self.arduino.current_distance <= 0 or self.faces_detected:
            return
        
        distance = self.arduino.current_distance
        
        # Only speak obstacle alerts if no faces are currently detected
        if not self.faces_detected:
            if self.voice.use_kinyarwanda:
                # Kinyarwanda obstacle alerts
                if distance < 20:
                    self.voice.speak(f"Witondere! Inzitizi iri kure ya santimetero {distance}!", "distance_critical", 3)
                elif distance < 40:
                    self.voice.speak(f"Akaga! Inzitizi iri kure ya santimetero {distance}!", "distance_danger", 4)
                elif distance < 70:
                    self.voice.speak(f"Burira! Inzitizi iri kure ya santimetero {distance}", "distance_warning", 5)
            else:
                # English obstacle alerts
                if distance < 20:
                    self.voice.speak(f"Emergency! Obstacle at {distance} centimeters!", "distance_critical", 3)
                elif distance < 40:
                    self.voice.speak(f"Danger! Obstacle at {distance} centimeters!", "distance_danger", 4)
                elif distance < 70:
                    self.voice.speak(f"Warning! Obstacle at {distance} centimeters", "distance_warning", 5)
    
    def draw_display(self, frame, detected_faces):
        """Draw UI overlay"""
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (1000, 180), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        status = "ACTIVE" if self.faces_detected else "SCANNING"
        
        lines = [
            " SMART GLASSES - FIXED VERSION",
            f"Status: {status} | Distance: {self.arduino.current_distance} cm",
            f"Faces Detected: {len(detected_faces)}",
            "Press 'Q' to quit"
        ]
        
        y = 30
        for line in lines:
            color = (0, 255, 0) if self.faces_detected else (255, 255, 0)
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            y += 35
        
        # Draw face boxes
        for face in detected_faces:
            top, right, bottom, left = face['location']
            name = face['name']
            confidence = face['confidence']
            distance = face['distance']
            
            # Color: Green for recognized, Yellow for unknown
            color = (0, 255, 0) if name != "Unknown Person" else (0, 255, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
            
            # Label with distance value
            if name != "Unknown Person":
                label = f"{name} ({confidence:.2f} | d:{distance:.3f})"
            else:
                label = f"Unknown (d:{distance:.3f})"
                
            # Label background
            label_height = 30
            cv2.rectangle(frame, (left, top-label_height), (right, top), color, -1)
            cv2.putText(frame, label, (left+5, top-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    def run(self):
        """Main system loop"""
        print("\n Starting face detection system...")
        print(" Using reliable OpenCV detection only")
        print(" No memory errors")
        print(" Smooth operation")
        print("\nPress 'Q' to quit\n")
        
        if not self.phone_camera.cap:
            print(" Phone camera not connected")
            return
        
        self.running = True
        
        try:
            while self.running:
                ret, frame = self.phone_camera.read()
                
                if not ret:
                    print(" Lost connection to phone camera")
                    break
                
                # Reset face detection flag
                self.faces_detected = False
                
                # Read Arduino for distance data
                if self.arduino.connected:
                    msg = self.arduino.read()
                    if msg:
                        self.arduino.process_message(msg)
                
                # Face recognition
                detected_faces = self.recognize_and_speak_faces(frame)
                
                # Only speak distance alerts if NO faces detected
                if len(detected_faces) == 0:
                    self.speak_distance_alerts()
                
                # Draw UI
                self.draw_display(frame, detected_faces)
                
                # Display
                cv2.imshow('Smart Glasses - FIXED', frame)
                
                # Keys
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                
                time.sleep(0.05)  # Slight delay to reduce CPU load
        
        except KeyboardInterrupt:
            print("\n Stopped by user")
        except Exception as e:
            print(f"\n Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.phone_camera.release()
            cv2.destroyAllWindows()
            self.arduino.close()
            print("\n System stopped")

def main():
    print("\n" + "=" * 70)
    print("SMART GLASSES - FIXED VERSION")
    print("No errors, smooth operation, reliable recognition")
    print("=" * 70)
    
    # Language selection
    print("\nChoose language / Hitamo ururimi:")
    print("1. English")
    print("2. Kinyarwanda")
    lang_choice = input("Enter choice [2]: ").strip()
    use_kinyarwanda = True if lang_choice != "1" else False
    
    phone_ip = input("Enter your phone's IP address [192.168.1.69]: ").strip()
    if not phone_ip:
        phone_ip = "192.168.1.69"
    
    system = SmartGlassesPhone(phone_ip=phone_ip)
    system.voice.use_kinyarwanda = use_kinyarwanda
    
    if use_kinyarwanda:
        print("\n Ururimi: Kinyarwanda")
    else:
        print("\n Language: English")
    
    try:
        system.run()
    except Exception as e:
        print(f"\n Fatal error: {e}")
    
    if use_kinyarwanda:
        print("\n Murabeho!")
    else:
        print("\n Goodbye!")

if __name__ == "__main__":
    main()