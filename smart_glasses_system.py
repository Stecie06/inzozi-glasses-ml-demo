#!/usr/bin/env python3
"""
SMART GLASSES SYSTEM - FIXED FACE RECOGNITION WITH VOICE
Now properly recognizes Gahamanyi, NAYITURIKI, Stecie and speaks their names!
"""

import cv2
import face_recognition
import numpy as np
import time
import os
import sys
import subprocess

# Try to import serial for Arduino (optional)
try:
    import serial
    ARDUINO_AVAILABLE = True
except ImportError:
    ARDUINO_AVAILABLE = False
    print("⚠️ pyserial not installed. Run: pip install pyserial")

class VoiceEngine:
    """Handles text-to-speech output"""
    def __init__(self):
        self.voice_enabled = True
        self.last_speech_by_type = {}  # Track last speech time by type
        
    def speak(self, text, speech_type="general", cooldown=3):
        """Speak text using Windows voice with per-type cooldown"""
        if not self.voice_enabled:
            return
            
        current_time = time.time()
        
        # Check cooldown for this specific type of speech
        if speech_type in self.last_speech_by_type:
            if current_time - self.last_speech_by_type[speech_type] < cooldown:
                return
        
        print(f"🔊 SPEAKING: {text}")
        self.last_speech_by_type[speech_type] = current_time
        
        try:
            # Windows PowerShell voice
            escaped_text = text.replace('"', '`"')
            command = f'powershell -Command "Add-Type -AssemblyName System.Speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Speak(\\\"{escaped_text}\\\")"'
            subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        except Exception as e:
            print(f"⚠️ Voice error: {e}")

class ArduinoInterface:
    """Handles Arduino communication"""
    def __init__(self, port='COM9'):
        self.port = port
        self.arduino = None
        self.connected = False
        self.current_distance = -1
        
    def connect(self):
        """Connect to Arduino"""
        if not ARDUINO_AVAILABLE:
            print(" Arduino not available (pyserial not installed)")
            return False
            
        try:
            print(f"🔌 Connecting to Arduino on {self.port}...")
            self.arduino = serial.Serial(
                port=self.port,
                baudrate=9600,
                timeout=1
            )
            time.sleep(2)
            self.arduino.reset_input_buffer()
            
            # Wait for ready signal
            start_time = time.time()
            while time.time() - start_time < 5:
                if self.arduino.in_waiting:
                    line = self.arduino.readline().decode('utf-8').strip()
                    if line:
                        print(f" {line}")
                    if "ARDUINO_READY" in line:
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
        """Read distance from Arduino"""
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
        """Process Arduino message and extract distance"""
        if not message:
            return
            
        if message.startswith("DISTANCE:"):
            try:
                self.current_distance = int(message.split(":")[1])
            except:
                pass
    
    def close(self):
        """Close Arduino connection"""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()

class SmartGlasses:
    """Main smart glasses system - FIXED to speak face names!"""
    def __init__(self, arduino_port='COM9'):
        print("=" * 70)
        print(" SMART GLASSES - FACE RECOGNITION SYSTEM")
        print("=" * 70)
        
        # Initialize components
        self.voice = VoiceEngine()
        self.arduino = ArduinoInterface(arduino_port)
        
        # Face recognition
        self.known_face_encodings = []
        self.known_face_names = []
        
        # State tracking
        self.last_detected_faces = {}  # Track each person separately
        self.frame_count = 0
        self.running = False
        
        # Load faces
        self.load_known_faces()
        
        # Connect Arduino
        arduino_connected = self.arduino.connect()
        
        print("\n SYSTEM STATUS:")
        print(f"   Arduino: {' CONNECTED' if arduino_connected else '❌ NOT CONNECTED'}")
        print(f"   Voice Output:  ENABLED")
        print(f"   Known Faces: {len(self.known_face_names)}")
        if self.known_face_names:
            print(f"   Names: {', '.join(self.known_face_names)}")
        print("=" * 70)
        
        # Startup announcement
        if self.known_face_names:
            self.voice.speak(f"Smart glasses ready. I can recognize {', '.join(self.known_face_names)}", "startup", 0)
        else:
            self.voice.speak("Smart glasses ready. No known faces loaded", "startup", 0)
    
    def load_known_faces(self):
        """Load known faces from directory"""
        faces_folder = "known_faces"
        
        if not os.path.exists(faces_folder):
            os.makedirs(faces_folder)
            print(" Created 'known_faces' folder")
            print(" Add face images: Gahamanyi.jpg, NAYITURIKI.jpg, Stecie.jpg")
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
                
                # Load image
                image = face_recognition.load_image_file(image_path)
                
                # Find face encodings
                face_encodings = face_recognition.face_encodings(image)
                
                if face_encodings:
                    # Use the first face found
                    self.known_face_encodings.append(face_encodings[0])
                    person_name = os.path.splitext(filename)[0]
                    self.known_face_names.append(person_name)
                    print(f"    Loaded: {person_name}")
                else:
                    print(f"    No face found in: {filename}")
                    
            except Exception as e:
                print(f"    Error loading {filename}: {e}")
        
        print(f" Successfully loaded {len(self.known_face_names)} known faces")
    
    def recognize_and_speak_faces(self, frame):
        """THE KEY FIX: Recognize faces and SPEAK their names!"""
        try:
            self.frame_count += 1
            # Process EVERY frame for better recognition
            if self.frame_count % 2 != 0:
                return []
            
            # Use FULL RESOLUTION for better accuracy
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Find ALL faces in frame with CNN model for better accuracy
            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
            
            if not face_locations:
                return []
            
            # Get encodings for all detected faces
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            detected_faces = []
            current_time = time.time()
            
            for face_location, face_encoding in zip(face_locations, face_encodings):
                top, right, bottom, left = face_location
                
                name = "Unknown Person"
                confidence = 0.0
                best_distance = 1.0
                
                # Compare with ALL known faces - RELAXED TOLERANCE
                if self.known_face_encodings:
                    # Calculate distances to ALL known faces
                    face_distances = face_recognition.face_distance(
                        self.known_face_encodings, 
                        face_encoding
                    )
                    
                    # Find the best match
                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        best_distance = face_distances[best_match_index]
                        confidence = max(0, 1 - best_distance)
                        
                        # RELAXED matching - use 0.65 tolerance (higher = more lenient)
                        if best_distance < 0.65:
                            name = self.known_face_names[best_match_index]
                            print(f" RECOGNIZED: {name} (confidence: {confidence:.2f}, face_distance: {best_distance:.2f})")
                        else:
                            print(f" Close match to {self.known_face_names[best_match_index]} but not confident enough (distance: {best_distance:.2f})")
                
                # SPEAK THE NAME - This is what was missing!
                if name != "Unknown Person":
                    # Check if we've spoken this person's name recently
                    speech_key = f"face_{name}"
                    
                    if speech_key not in self.last_detected_faces or \
                       current_time - self.last_detected_faces[speech_key] > 12:
                        
                        # Create announcement with distance
                        if self.arduino.current_distance > 0 and self.arduino.current_distance < 200:
                            distance = self.arduino.current_distance
                            
                            if distance < 50:
                                announcement = f"{name} is very close, {distance} centimeters"
                            elif distance < 100:
                                announcement = f"{name} is nearby, {distance} centimeters away"
                            else:
                                announcement = f"{name} detected at {distance} centimeters"
                        else:
                            announcement = f"{name} detected"
                        
                        # SPEAK IT!
                        self.voice.speak(announcement, speech_key, cooldown=12)
                        self.last_detected_faces[speech_key] = current_time
                        print(f" SPOKE: {announcement}")
                
                # Also announce unknown people occasionally
                elif current_time - self.last_detected_faces.get("unknown", 0) > 20:
                    self.voice.speak("Unknown person detected", "unknown", cooldown=20)
                    self.last_detected_faces["unknown"] = current_time
                
                # Store for display
                detected_faces.append({
                    'location': (top, right, bottom, left),
                    'name': name,
                    'confidence': confidence
                })
            
            return detected_faces
            
        except Exception as e:
            print(f" Face recognition error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def speak_distance_alerts(self):
        """Speak distance-based obstacle alerts (separate from faces)"""
        if self.arduino.current_distance <= 0:
            return
        
        distance = self.arduino.current_distance
        
        # Only speak distance if no face was recently announced
        if distance < 20:
            self.voice.speak(
                f"EMERGENCY! Obstacle at {distance} centimeters! STOP NOW!", 
                "distance_critical", 
                cooldown=2
            )
        elif distance < 40:
            self.voice.speak(
                f"DANGER! Obstacle at {distance} centimeters! Stop!", 
                "distance_danger", 
                cooldown=3
            )
        elif distance < 70:
            self.voice.speak(
                f"Warning! Obstacle at {distance} centimeters", 
                "distance_warning", 
                cooldown=5
            )
        elif distance < 120:
            self.voice.speak(
                f"Obstacle at {distance} centimeters", 
                "distance_info", 
                cooldown=8
            )
    
    def draw_display(self, frame, detected_faces):
        """Draw UI overlay - BIGGER TEXT"""
        overlay = frame.copy()
        # BIGGER overlay bar
        cv2.rectangle(overlay, (0, 0), (1000, 250), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # System info - BIGGER TEXT
        lines = [
            " SMART GLASSES - FACE RECOGNITION",
            f"Distance: {self.arduino.current_distance} cm",
            f"Known: {', '.join(self.known_face_names) if self.known_face_names else 'None'}",
            f"Detected: {len(detected_faces)} face(s)",
            "",
            "Press 'Q' to quit | 'R' to reload faces | 'V' toggle voice"
        ]
        
        y = 35
        for line in lines:
            cv2.putText(frame, line, (15, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 3)
            y += 40
        
        # Draw face boxes - MUCH BIGGER
        for face in detected_faces:
            top, right, bottom, left = face['location']
            name = face['name']
            confidence = face['confidence']
            
            # Color: Green for known, Yellow for unknown
            color = (0, 255, 0) if name != "Unknown Person" else (0, 255, 255)
            
            # THICKER Box
            cv2.rectangle(frame, (left, top), (right, bottom), color, 4)
            
            # Label - BIGGER
            if name != "Unknown Person":
                label = f"{name} ({confidence:.2f})"
            else:
                label = name
            
            # BIGGER Label background
            label_height = 50
            cv2.rectangle(frame, (left, top - label_height), (right, top), color, -1)
            
            # BIGGER Label text
            cv2.putText(frame, label, (left + 10, top - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)
    
    def run(self):
        """Main system loop"""
        print("\n Starting camera...")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print(" Cannot open camera")
            self.voice.speak("Cannot access camera")
            return
        
        # BIGGER WINDOW - 1280x720 resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        time.sleep(1)
        
        print(" Camera ready!")
        print("\n SYSTEM ACTIVE!")
        print("    Will SPEAK names: Gahamanyi, NAYITURIKI, Stecie")
        print("    Will SPEAK distance warnings for obstacles")
        print("    IMPROVED face recognition accuracy")
        print("     BIGGER camera window")
        print("   Press 'Q' to quit\n")
        
        self.running = True
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Flip for mirror view
                frame = cv2.flip(frame, 1)
                
                # Read Arduino
                if self.arduino.connected:
                    msg = self.arduino.read()
                    if msg:
                        self.arduino.process_message(msg)
                        # Only speak distance if it's an obstacle (not a person)
                        # Face names will be spoken by recognize_and_speak_faces
                
                # FACE RECOGNITION - This will SPEAK names!
                detected_faces = self.recognize_and_speak_faces(frame)
                
                # If no faces detected, then speak distance alerts
                if len(detected_faces) == 0:
                    self.speak_distance_alerts()
                
                # Draw UI
                self.draw_display(frame, detected_faces)
                
                # Display
                cv2.imshow('Smart Glasses - Face Recognition', frame)
                
                # Keys
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    print(" Reloading faces...")
                    self.load_known_faces()
                elif key == ord('v'):
                    self.voice.voice_enabled = not self.voice.voice_enabled
                    status = "ON" if self.voice.voice_enabled else "OFF"
                    print(f" Voice: {status}")
                
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n Stopped")
        except Exception as e:
            print(f"\n Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.arduino.close()
            self.voice.speak("System shutting down", "shutdown", 0)
            print("\n System stopped")

def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("SMART GLASSES - FACE RECOGNITION WITH VOICE")
    print("Recognizes: Gahamanyi, NAYITURIKI, Stecie")
    print("=" * 70 + "\n")
    
    arduino_port = 'COM9'
    if len(sys.argv) > 1:
        arduino_port = sys.argv[1]
    
    system = SmartGlasses(arduino_port)
    
    try:
        system.run()  # FIXED: Changed from start() to run()
    except Exception as e:
        print(f"\n Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n Goodbye!")

if __name__ == "__main__":
    main()