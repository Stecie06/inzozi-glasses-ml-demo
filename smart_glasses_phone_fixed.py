import cv2
import numpy as np
import time
import os
import subprocess
import requests
from pathlib import Path

# ---- Additional imports required by the base class below ----
import re
import glob
import threading
import queue

try:
    import face_recognition
except ImportError:
    face_recognition = None
    print(" face_recognition not installed. Install with: pip install face_recognition")

try:
    import serial
except ImportError:
    serial = None
    print(" pyserial not installed. Install with: pip install pyserial")

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
    print(" pyttsx3 not installed. Install with: pip install pyttsx3")

try:
    import pythoncom
except ImportError:
    pythoncom = None


# ============================================================
# PHONE CAMERA CLASS (FIXED: threaded reader + auto-reconnect)
# ============================================================
class PhoneCamera:

    # Common IP Webcam endpoints, tried in order until one works
    CANDIDATE_PATHS = ["/video", "/videofeed", ""]
    FRAME_ROTATION = cv2.ROTATE_90_COUNTERCLOCKWISE

    def __init__(self, phone_ip, port=8080):
        self.phone_ip = phone_ip
        self.port = port
        self.cap = None
        self.connected_url = None
        self._lock = threading.Lock()
        self._latest_frame = None
        self._running = False
        self._thread = None
        self._connect()

    def _open_capture(self, url):
        cap = cv2.VideoCapture(url)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        return cap

    def _connect(self):
        if not self.phone_ip:
            print(" No phone IP provided, camera not connected")
            return

        for path in self.CANDIDATE_PATHS:
            url = f"http://{self.phone_ip}:{self.port}{path}"
            print(f" Trying phone camera at {url} ...")
            cap = self._open_capture(url)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.cap = cap
                    self.connected_url = url
                    print(f" Phone camera connected: {url}")
                    print(f" Frame rotation correction: {self.FRAME_ROTATION} "
                          f"(change PhoneCamera.FRAME_ROTATION if your video looks sideways)")
                    self._start_reader_thread()
                    return
            cap.release()

        print(" Could not reach phone stream, falling back to local webcam (index 0)")
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            self.cap = cap
            self.connected_url = "local:0"
            self._start_reader_thread()
        else:
            print(" No camera source available")
            self.cap = None

    def _start_reader_thread(self):
        self._running = True
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def _reader_loop(self):
        fail_count = 0
        while self._running:
            if self.cap is None:
                time.sleep(0.5)
                continue
            try:
                ret, frame = self.cap.read()
            except Exception as e:
                ret, frame = False, None
                print(f" Camera read exception: {e}")

            if not ret or frame is None:
                fail_count += 1
                if fail_count <= 3:
                    time.sleep(0.05)
                    continue
                print(" Camera read failing repeatedly, attempting reconnect...")
                self._reconnect()
                fail_count = 0
                continue

            fail_count = 0
            if self.FRAME_ROTATION is not None:
                frame = cv2.rotate(frame, self.FRAME_ROTATION)
            with self._lock:
                self._latest_frame = frame

    def _reconnect(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        if self.connected_url == "local:0":
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                self.cap = cap
                print(" Reconnected to local webcam")
                return
            cap.release()
        elif self.connected_url:
            cap = self._open_capture(self.connected_url)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.cap = cap
                    print(f" Reconnected to phone camera: {self.connected_url}")
                    return
            cap.release()

        time.sleep(1.0)
        for path in self.CANDIDATE_PATHS:
            url = f"http://{self.phone_ip}:{self.port}{path}"
            cap = self._open_capture(url)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    self.cap = cap
                    self.connected_url = url
                    print(f" Reconnected to phone camera: {url}")
                    return
            cap.release()

        print(" Reconnect attempt failed, will retry...")
        time.sleep(1.0)

    def read(self):
        with self._lock:
            if self._latest_frame is None:
                return False, None
            return True, self._latest_frame.copy()

    def release(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
        if self.cap is not None:
            self.cap.release()
            self.cap = None


# ============================================================
# ARDUINO SERIAL READER CLASS
# ============================================================
class ArduinoReader:
    """Reads distance data from an Arduino over serial."""

    def __init__(self, port='COM12', baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.connected = False
        self.serial_conn = None
        self.current_distance = 999

        if serial is None:
            print(" pyserial not available, Arduino distance features disabled")
            return

        try:
            self.serial_conn = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(2)
            self.connected = True
            print(f" Arduino connected on {port}")
        except Exception as e:
            print(f" Could not connect to Arduino on {port}: {e}")
            print("   Distance alerts will be disabled")
            self.connected = False

    def read(self):
        if not self.connected or self.serial_conn is None:
            return None
        try:
            if self.serial_conn.in_waiting > 0:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                return line if line else None
        except Exception as e:
            print(f"Arduino read error: {e}")
        return None

    RESET_MARKERS = ("ARDUINO_READY", "SYSTEM READY", "DISTANCE_SENSOR", "SMART_GLASSES")
    DISTANCE_PATTERN = re.compile(r'DIST(?:ANCE)?\s*[:=]\s*(\d+(?:\.\d+)?)', re.IGNORECASE)

    def process_message(self, msg):
        if not msg:
            return

        print(f" [ARDUINO RAW] '{msg}'")

        upper_msg = msg.upper()
        if any(marker in upper_msg for marker in self.RESET_MARKERS):
            print(f" [ARDUINO RESET DETECTED] '{msg}' - the Arduino just "
                  f"(re)booted mid-session. Check the USB cable/power "
                  f"connection; the last known distance is being kept "
                  f"({self.current_distance} cm) until a real reading arrives.")
            return

        match = self.DISTANCE_PATTERN.search(msg)
        if match:
            try:
                value = int(float(match.group(1)))
                self.current_distance = value
                print(f" [ARDUINO PARSED] distance={value} cm")
            except ValueError:
                pass
        else:
            print(f" [ARDUINO PARSED] line did not match a distance reading, ignored")

    def close(self):
        if self.serial_conn is not None:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.connected = False


# ============================================================
# VOICE / TTS ENGINE CLASS
# ============================================================
class VoiceEngine:

    MAX_QUEUE_SIZE = 4

    def __init__(self, use_kinyarwanda=False):
        self.use_kinyarwanda = use_kinyarwanda
        self.voice_enabled = True
        self.last_spoken = {}
        self._lock = threading.Lock()

        self.engine_available = pyttsx3 is not None
        if not self.engine_available:
            print(" Voice engine disabled (pyttsx3 not installed)")
            return

        self._queue = queue.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self):
        com_initialized = False
        if pythoncom is not None:
            try:
                pythoncom.CoInitialize()
                com_initialized = True
            except Exception as e:
                print(f"COM initialization warning: {e}")

        try:
            test_engine = pyttsx3.init()
            test_engine.stop()
            del test_engine
        except Exception as e:
            print(f"Voice engine init error: {e}")
            self.engine_available = False
            if com_initialized:
                pythoncom.CoUninitialize()
            return

        while True:
            text = self._queue.get()
            if text is None:
                break
            try:
                # Fresh engine every time - this is the actual fix.
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                del engine
                print(f" [VOICE OUTPUT CONFIRMED] {text}")
            except Exception as e:
                print(f"Voice engine error: {e}")
            finally:
                self._queue.task_done()

        if com_initialized:
            pythoncom.CoUninitialize()

    def speak(self, text, key="default", cooldown=5, force=False):
        if not self.voice_enabled:
            return

        current_time = time.time()

        if not force:
            with self._lock:
                last_time = self.last_spoken.get(key, 0)
                if cooldown > 0 and (current_time - last_time) < cooldown:
                    return
                self.last_spoken[key] = current_time

        print(f" [VOICE] {text}")

        if self.engine_available:
            try:
                self._queue.put_nowait(text)
            except queue.Full:
                try:
                    dropped = self._queue.get_nowait()
                    self._queue.task_done()
                    print(f" [VOICE QUEUE FULL] dropped stale message: '{dropped}'")
                except queue.Empty:
                    pass
                try:
                    self._queue.put_nowait(text)
                except queue.Full:
                    pass

    def speak_immediate(self, text):
        """Speak immediately without any cooldown."""
        self.speak(text, key="immediate", cooldown=0, force=True)

    def stop(self):
        if self.engine_available:
            try:
                self._queue.put_nowait(None)
            except queue.Full:
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except queue.Empty:
                    pass
                self._queue.put_nowait(None)


# ============================================================
# BASE CLASS: SMART GLASSES COMPLETE
# ============================================================
class SmartGlassesComplete:
    """Base system: phone camera + Arduino distance + face recognition + voice."""

    KNOWN_FACES_DIR = "known_faces"
    DISTANCE_ALERT_THRESHOLD_CM = 50
    DISTANCE_ALERT_COOLDOWN = 6

    def __init__(self, phone_ip="192.168.2.102", arduino_port='COM12', use_kinyarwanda=False):
        print("\n" + "=" * 70)
        print(" SMART GLASSES - CORE SYSTEM INIT")
        print("=" * 70)

        self.voice = VoiceEngine(use_kinyarwanda=use_kinyarwanda)
        self.phone_camera = PhoneCamera(phone_ip)
        self.arduino = ArduinoReader(arduino_port)

        self.known_face_encodings = []
        self.known_face_names = []
        self.load_known_faces()

        self.frame_count = 0
        self.last_detected_faces = {}
        self.running = False
        self._last_distance_alert = 0

        print("=" * 70)

        startup_msg = "System ready with face recognition" if not use_kinyarwanda else "Sisitemu iteguye"
        self.voice.speak_immediate(startup_msg)

    def load_known_faces(self):
        self.known_face_encodings = []
        self.known_face_names = []

        if face_recognition is None:
            print(" face_recognition not installed - cannot load known faces")
            return

        if not os.path.isdir(self.KNOWN_FACES_DIR):
            print(f" '{self.KNOWN_FACES_DIR}' folder not found - no known faces loaded")
            return

        resolved = {}
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"):
            for p in glob.glob(os.path.join(self.KNOWN_FACES_DIR, ext)):
                key = os.path.normcase(os.path.abspath(p))
                resolved.setdefault(key, p)

        print(f" Loading known faces from '{self.KNOWN_FACES_DIR}'...")
        for path in sorted(resolved.values()):
            name = os.path.splitext(os.path.basename(path))[0]
            try:
                image = face_recognition.load_image_file(path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    self.known_face_encodings.append(encodings[0])
                    self.known_face_names.append(name)
                    print(f"    Loaded: {name}")
                else:
                    print(f"    No face found in {path}, skipping")
            except Exception as e:
                print(f"    Error loading {path}: {e}")

        print(f" Total known faces loaded: {len(self.known_face_names)}")

    def speak_distance_alert(self):
        distance = self.arduino.current_distance
        if distance <= 0 or distance >= self.DISTANCE_ALERT_THRESHOLD_CM:
            return

        current_time = time.time()
        if current_time - self._last_distance_alert < self.DISTANCE_ALERT_COOLDOWN:
            return

        if self.voice.use_kinyarwanda:
            message = f"Itonde, hari ikintu ku ntera ya santimetero {distance}"
        else:
            message = f"Caution, object {distance} centimeters ahead"

        self.voice.speak(message, "distance_alert", cooldown=self.DISTANCE_ALERT_COOLDOWN, force=True)
        self._last_distance_alert = current_time


# ============================================================
# OBJECT DETECTION CLASS
# ============================================================
class ObjectDetector:
    """Handles object detection using YOLOv8"""

    def __init__(self):
        self.model = None
        self.class_names = []
        self.is_available = False
        self.last_detections = {}
        self.detection_cooldown = 5

        try:
            from ultralytics import YOLO

            model_path = "yolov8n.pt"
            if not os.path.exists(model_path):
                print(" Downloading YOLOv8 model...")

            self.model = YOLO(model_path)
            self.is_available = True
            print(" YOLOv8 loaded successfully!")
            self.class_names = self.model.names

        except ImportError:
            print(" Ultralytics not installed. Install with: pip install ultralytics")
            print("   Object detection will be disabled")
        except Exception as e:
            print(f" Error loading YOLO: {e}")

    def detect_objects(self, frame, confidence_threshold=0.5):
        if not self.is_available or self.model is None:
            return [], []

        try:
            results = self.model(frame, conf=confidence_threshold, verbose=False)

            detected_objects = []
            boxes = []

            for result in results:
                for box in result.boxes:
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = self.class_names[class_id]
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                    detected_objects.append({
                        'class': class_name,
                        'confidence': confidence,
                        'box': (x1, y1, x2, y2)
                    })
                    boxes.append((x1, y1, x2, y2))

            return detected_objects, boxes

        except Exception as e:
            print(f"Error in object detection: {e}")
            return [], []

    def speak_detection(self, objects, voice_engine, max_objects=3):
        if not objects:
            return

        current_time = time.time()
        spoken_objects = []

        objects.sort(key=lambda x: x['confidence'], reverse=True)
        objects = objects[:max_objects]

        for obj in objects:
            class_name = obj['class']

            if class_name not in self.last_detections or \
               current_time - self.last_detections[class_name] > self.detection_cooldown:

                if class_name not in spoken_objects:
                    spoken_objects.append(class_name)
                    self.last_detections[class_name] = current_time

        if spoken_objects:
            if len(spoken_objects) == 1:
                message = f"Detected {spoken_objects[0]}"
            elif len(spoken_objects) == 2:
                message = f"Detected {spoken_objects[0]} and {spoken_objects[1]}"
            else:
                message = f"Detected {', '.join(spoken_objects[:-1])}, and {spoken_objects[-1]}"

            voice_engine.speak(message, "object_detection", cooldown=0, force=True)
            print(f" {message}")

# ============================================================
# EMOTION DETECTION CLASS
# ============================================================
class EmotionDetector:
    """Handles facial emotion detection using DeepFace or FER"""

    def __init__(self):
        self.is_available = False
        self.emotion_model = None
        self.last_emotions = {}
        self.emotion_cooldown = 8

        try:
            from deepface import DeepFace
            self.emotion_model = "DeepFace"
            self.is_available = True
            print(" DeepFace emotion detection loaded!")

        except ImportError:
            try:
                from fer import FER
                self.emotion_model = FER()
                self.is_available = True
                print(" FER emotion detection loaded!")
            except ImportError:
                print(" Emotion detection not available. Install with:")
                print("   pip install deepface  # OR")
                print("   pip install fer")

    def detect_emotion(self, face_image):
        if not self.is_available:
            return None

        try:
            if self.emotion_model == "DeepFace":
                from deepface import DeepFace
                result = DeepFace.analyze(face_image, actions=['emotion'], enforce_detection=False)
                if result and len(result) > 0:
                    emotions = result[0]['emotion']
                    dominant_emotion = max(emotions, key=emotions.get)
                    confidence = emotions[dominant_emotion] / 100.0
                    return dominant_emotion, confidence

            elif hasattr(self.emotion_model, 'detect_emotions'):
                result = self.emotion_model.detect_emotions(face_image)
                if result and len(result) > 0:
                    emotions = result[0]['emotions']
                    dominant_emotion = max(emotions, key=emotions.get)
                    confidence = emotions[dominant_emotion] / 100.0
                    return dominant_emotion, confidence

        except Exception as e:
            print(f"Emotion detection error: {e}")
            return None

        return None

    def speak_emotion(self, person_name, emotion, voice_engine):
        """Speak detected emotion - force=True so every detection is announced"""
        if not emotion or not person_name:
            return

        current_time = time.time()
        key = f"emotion_{person_name}"

        emotion_messages = {
            'happy': "looks happy",
            'sad': "looks sad",
            'angry': "looks angry",
            'surprise': "looks surprised",
            'fear': "looks scared",
            'disgust': "looks disgusted",
            'neutral': "looks neutral"
        }

        message = emotion_messages.get(emotion.lower(), f"looks {emotion}")

        voice_engine.speak(f"{person_name} {message}", key, cooldown=8, force=True)
        self.last_emotions[key] = current_time
        print(f" {person_name}: {emotion}")

# ============================================================
# SCENE RECOGNITION CLASS
# ============================================================
class SceneRecognizer:
    """Handles scene/place recognition using YOLO or CLIP"""

    def __init__(self):
        self.is_available = False
        self.model = None
        self.last_scene = None
        self.scene_cooldown = 8  # seconds - matches SCENE_CHECK_INTERVAL in run()

        try:
            from ultralytics import YOLO
            self.model = YOLO("yolov8n.pt")
            self.is_available = True
            print(" Scene recognition loaded!")

            self.outdoor_indicators = ['person', 'car', 'tree', 'sky', 'building', 'road']
            self.indoor_indicators = ['chair', 'table', 'tv', 'person', 'book', 'phone']

        except ImportError:
            print(" Scene recognition not available")

    def classify_scene(self, frame):
        if not self.is_available or self.model is None:
            return "Unknown"

        try:
            results = self.model(frame, verbose=False)

            outdoor_score = 0
            indoor_score = 0

            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    class_name = self.model.names[class_id]

                    if class_name in self.outdoor_indicators:
                        outdoor_score += float(box.conf[0])
                    elif class_name in self.indoor_indicators:
                        indoor_score += float(box.conf[0])

            if outdoor_score > indoor_score and outdoor_score > 0.5:
                return "Outdoor"
            elif indoor_score > outdoor_score and indoor_score > 0.5:
                return "Indoor"
            else:
                return "Unknown"

        except Exception as e:
            print(f"Scene classification error: {e}")
            return "Unknown"

    def speak_scene(self, scene_type, voice_engine):
        if scene_type == "Unknown":
            return

        current_time = time.time()

        if self.last_scene is None or \
           current_time - self.last_scene > self.scene_cooldown:

            voice_engine.speak(f"You are {scene_type.lower()}", "scene", cooldown=15, force=True)
            self.last_scene = current_time
            print(f" Scene: {scene_type}")

# ============================================================
# MAIN SMART GLASSES WITH ML INTEGRATION
# ============================================================

class SmartGlassesWithML(SmartGlassesComplete):
    """Extended smart glasses with ML capabilities"""

    def __init__(self, phone_ip="192.168.2.102", arduino_port='COM12',
                 use_kinyarwanda=False, enable_object_detection=True,
                 enable_emotion_detection=True):

        super().__init__(phone_ip, arduino_port, use_kinyarwanda)

        print("\n" + "=" * 70)
        print(" MACHINE LEARNING MODULES")
        print("=" * 70)

        self.object_detector = ObjectDetector() if enable_object_detection else None
        self.emotion_detector = EmotionDetector() if enable_emotion_detection else None
        self.scene_recognizer = SceneRecognizer()

        self.ml_enabled = True
        self.detection_interval = 10
        self.ml_frame_counter = 0

        print("\n ML MODULE STATUS:")
        print(f"   Object Detection: {'✅' if self.object_detector and self.object_detector.is_available else '❌'}")
        print(f"   Emotion Detection: {'✅' if self.emotion_detector and self.emotion_detector.is_available else '❌'}")
        print(f"   Scene Recognition: {'✅' if self.scene_recognizer and self.scene_recognizer.is_available else '❌'}")
        print("=" * 70)

        if use_kinyarwanda:
            self.voice.speak_immediate("Sisitemu ifite ubuhanga bwa machine learning")
        else:
            self.voice.speak_immediate("System ready with machine learning capabilities")

    def run(self):
        """Main system loop with ML integration"""
        print("\n Starting ML-enhanced smart glasses...")

        if not self.phone_camera.cap:
            print(" Phone camera not connected")
            return

        print("\n SYSTEM ACTIVE WITH ML FEATURES!")
        print("    Face Recognition: ACTIVE")
        print("    Object Detection: ACTIVE")
        print("    Emotion Detection: ACTIVE")
        print("    Scene Recognition: ACTIVE")
        print("\n CONTROLS:")
        print("   Press 'Q' - Quit")
        print("   Press 'V' - Toggle voice ON/OFF")
        print("   Press 'L' - Switch language (English/Kinyarwanda)")
        print("   Press 'R' - Reload faces")
        print("   Press 'M' - Toggle ML features ON/OFF")
        print("   Press 'O' - Object detection on/off")
        print("   Press 'E' - Emotion detection on/off")
        print("\n" + "=" * 50 + "\n")

        self.running = True
        consecutive_missed_frames = 0
        MAX_CONSECUTIVE_MISSES = 150

        last_spoken_face = {}
        last_scene_check = [0.0]
        SCENE_CHECK_INTERVAL = 8.0  # seconds

        try:
            while self.running:
                ret, frame = self.phone_camera.read()

                if not ret:
                    consecutive_missed_frames += 1
                    if consecutive_missed_frames == 1:
                        print(" Waiting for camera frame...")
                    if consecutive_missed_frames > MAX_CONSECUTIVE_MISSES:
                        print(" Lost connection to phone camera (no frames for too long)")
                        break
                    time.sleep(0.03)
                    continue

                consecutive_missed_frames = 0
                self.frame_count += 1
                self.ml_frame_counter += 1

                if self.arduino.connected:
                    msg = self.arduino.read()
                    if msg:
                        self.arduino.process_message(msg)

                if self.frame_count % 3 == 0:
                    small_frame = cv2.resize(frame, (0, 0), fx=0.75, fy=0.75)
                    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    rgb_small = np.ascontiguousarray(rgb_small)

                    face_locations = face_recognition.face_locations(
                        rgb_small, number_of_times_to_upsample=2, model="hog"
                    )

                    scale_back = 1.0 / 0.75

                    if face_locations:
                        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
                        current_time = time.time()

                        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                            top = int(top * scale_back)
                            right = int(right * scale_back)
                            bottom = int(bottom * scale_back)
                            left = int(left * scale_back)

                            name = "Unknown"

                            if self.known_face_encodings:
                                distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                                best_idx = np.argmin(distances)

                                if distances[best_idx] < 0.6:
                                    name = self.known_face_names[best_idx]

                                    speech_key = f"face_{name}"
                                    if speech_key not in last_spoken_face or \
                                       current_time - last_spoken_face[speech_key] > 8:

                                        if self.arduino.current_distance > 0 and self.arduino.current_distance < 200:
                                            if self.voice.use_kinyarwanda:
                                                announcement = f"{name} ari kure ya santimetero {self.arduino.current_distance}"
                                            else:
                                                announcement = f"{name} is {self.arduino.current_distance} centimeters away"
                                        else:
                                            announcement = name

                                        self.voice.speak(announcement, speech_key, cooldown=8, force=True)
                                        last_spoken_face[speech_key] = current_time

                                    # ML: EMOTION DETECTION - every detection announced
                                    if self.ml_enabled and self.emotion_detector and self.emotion_detector.is_available:
                                        face_crop = frame[top:bottom, left:right]
                                        if face_crop.size > 0:
                                            emotion_result = self.emotion_detector.detect_emotion(face_crop)
                                            if emotion_result:
                                                emotion, confidence = emotion_result
                                                if confidence > 0.4:
                                                    self.emotion_detector.speak_emotion(name, emotion, self.voice)

                            color = (0, 255, 0) if name != "Unknown" else (0, 255, 255)
                            cv2.rectangle(frame, (left, top), (right, bottom), color, 3)

                            label = name
                            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                            cv2.rectangle(frame, (left, top - label_size[1] - 10), (left + label_size[0], top), color, -1)
                            cv2.putText(frame, label, (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                        if not face_locations:
                            self.speak_distance_alert()
                    else:
                        self.speak_distance_alert()

                # ML: OBJECT DETECTION
                if self.ml_enabled and self.object_detector and self.object_detector.is_available:
                    if self.ml_frame_counter % self.detection_interval == 0:
                        objects, boxes = self.object_detector.detect_objects(frame)
                        if objects:
                            self.object_detector.speak_detection(objects, self.voice)

                            for obj in objects:
                                x1, y1, x2, y2 = obj['box']
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                                label = f"{obj['class']}: {obj['confidence']:.2f}"
                                cv2.putText(frame, label, (x1, y1 - 10),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

                # ML: SCENE RECOGNITION - time-based, not frame-count-based
                if self.ml_enabled and self.scene_recognizer and self.scene_recognizer.is_available:
                    if time.time() - last_scene_check[0] >= SCENE_CHECK_INTERVAL:
                        last_scene_check[0] = time.time()
                        scene_type = self.scene_recognizer.classify_scene(frame)
                        if scene_type != "Unknown":
                            self.scene_recognizer.speak_scene(scene_type, self.voice)

                lang_display = "KINYARWANDA" if self.voice.use_kinyarwanda else "ENGLISH"
                voice_status = "ON" if self.voice.voice_enabled else "OFF"
                ml_status = "ON" if self.ml_enabled else "OFF"

                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (450, 180), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

                y_offset = 30
                cv2.putText(frame, f"SMART GLASSES with ML - {lang_display}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                y_offset += 30
                cv2.putText(frame, f"Distance: {self.arduino.current_distance} cm", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 25
                cv2.putText(frame, f"Voice: {voice_status} | ML: {ml_status} | Faces: {len(self.known_face_names)}", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 25
                cv2.putText(frame, "Q:Quit V:Voice L:Language R:Reload M:ML O:Objects E:Emotions", (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

                cv2.imshow('Smart Glasses - Face Recognition with ML', frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n Quitting...")
                    break
                elif key == ord('v'):
                    self.voice.voice_enabled = not self.voice.voice_enabled
                    status = "ON" if self.voice.voice_enabled else "OFF"
                    print(f" Voice: {status}")
                    self.voice.speak(f"Voice {status}", "voice_toggle", 0, force=True)
                elif key == ord('l'):
                    self.voice.use_kinyarwanda = not self.voice.use_kinyarwanda
                    lang = "Kinyarwanda" if self.voice.use_kinyarwanda else "English"
                    print(f" Language: {lang}")
                    self.voice.speak(f"Language changed to {lang}", "lang_change", 0, force=True)
                elif key == ord('r'):
                    print(" Reloading faces...")
                    self.load_known_faces()
                    self.voice.speak("Faces reloaded", "reload", 0, force=True)
                elif key == ord('m'):
                    self.ml_enabled = not self.ml_enabled
                    status = "ON" if self.ml_enabled else "OFF"
                    print(f" ML features: {status}")
                    self.voice.speak(f"Machine learning {status}", "ml_toggle", 0, force=True)
                elif key == ord('o'):
                    if self.object_detector:
                        self.object_detector.is_available = not self.object_detector.is_available
                        status = "ON" if self.object_detector.is_available else "OFF"
                        print(f" Object detection: {status}")
                        self.voice.speak(f"Object detection {status}", "obj_toggle", 0, force=True)
                elif key == ord('e'):
                    if self.emotion_detector:
                        self.emotion_detector.is_available = not self.emotion_detector.is_available
                        status = "ON" if self.emotion_detector.is_available else "OFF"
                        print(f" Emotion detection: {status}")
                        self.voice.speak(f"Emotion detection {status}", "emo_toggle", 0, force=True)

                time.sleep(0.01)

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
            self.voice.stop()
            print("\n System stopped")

# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SMART GLASSES WITH MACHINE LEARNING")
    print("Phone Camera + Arduino + Face Recognition + ML")
    print("=" * 70)

    print("\n Checking ML dependencies...")
    try:
        import ultralytics
        print(" Ultralytics (YOLO) installed")
    except ImportError:
        print(" Ultralytics not installed")
        print("   Run: pip install ultralytics")

    try:
        import deepface
        print(" DeepFace installed")
    except ImportError:
        print(" DeepFace not installed")
        print("   Run: pip install deepface")

    print("\n" + "=" * 70)

    print("\n Select Language / Hitamo Ururimi:")
    print("   1. English")
    print("   2. Kinyarwanda")
    lang_choice = input("Enter choice (1 or 2): ").strip()
    use_kinyarwanda = (lang_choice == "2")

    print("\n Phone Camera Setup:")
    print("   Make sure IP Webcam app is running on your phone")
    phone_ip = input("   Enter phone IP address (from IP Webcam): ").strip()
    if not phone_ip:
        phone_ip = "192.168.2.102"
        print(f"   Using default: {phone_ip}")

    print("\n Arduino Setup (optional):")
    print("   If you don't have Arduino, just press Enter")
    arduino_port = input("   Enter COM port (e.g., COM12): ").strip()
    if not arduino_port:
        arduino_port = "COM9"
        print("   Skipping Arduino (will try COM9)")

    print("\n ML Features Configuration:")
    print("   Enable all ML features for best experience")
    enable_object = input("   Enable Object Detection? (y/n, default y): ").strip().lower() != 'n'
    enable_emotion = input("   Enable Emotion Detection? (y/n, default y): ").strip().lower() != 'n'

    print("\n" + "=" * 70)
    print(" Initializing ML-Enhanced Smart Glasses...")
    print("=" * 70)

    system = SmartGlassesWithML(
        phone_ip=phone_ip,
        arduino_port=arduino_port,
        use_kinyarwanda=use_kinyarwanda,
        enable_object_detection=enable_object,
        enable_emotion_detection=enable_emotion
    )


    try:
        system.run()
    except Exception as e:
        print(f"\n Fatal error: {e}")
        import traceback
        traceback.print_exc()

    print("\n Murabeho! / Goodbye!")