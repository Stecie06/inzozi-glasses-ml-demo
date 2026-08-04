# 🥽 Inzozi Glasses

## Bilingual AI-Powered Smart Glass System for Visually Impaired Users in Rwanda

### Project Overview
Inzozi Glasses (meaning "Dreams" in Kinyarwanda) is a wearable smart system that helps visually impaired users navigate indoors, recognize faces, detect emotions, and receive voice guidance in both Kinyarwanda and English.

### Features
- 🎯 **Object Detection (YOLOv8n)** — Detects everyday objects in view
- 👤 **Face Recognition** (`face_recognition`/dlib) — Recognizes registered people from `known_faces/`
- 😊 **Emotion Detection** (DeepFace) — Detects emotions on recognized faces
- 🏠 **Scene Recognition** — Classifies Indoor / Outdoor
- 📏 **Distance Alerts** — Optional Arduino ultrasonic sensor + vibration motor for obstacle warnings
- 🗣️ **Bilingual Voice** — Kinyarwanda + English text-to-speech and (in the standalone app) live language switching

### Live Demo
https://drive.google.com/file/d/1wEqMSUo27A3i6y9A18dbjFsulxuEa64-/view?usp=drive_link

### Final Product Demo
[https://drive.google.com/file/d/1mpUiJL8WEMc0P5mWOZPh33JizW_letGI/view?usp=drive_link](https://drive.google.com/file/d/1mpUiJL8WEMc0P5mWOZPh33JizW_letGI/view?usp=drive_link)

---

## ⚠️ Read this before "How to Use" — there are two runnable systems here, not one

This repo actually contains **two separate ways to run Inzozi Glasses**, plus a Windows `.exe` build of one of them. They are not the same thing, and the old "open `index.html` to see the complete simulation" instruction undersold what's actually here — one of these two is a real, working system, not a simulation.

| | What it is | How you run it | What powers detection |
|---|---|---|---|
| **A. Standalone hardware app** (the full-feature system) | Phone camera feed + optional Arduino distance sensor + face recognition + emotion detection + scene recognition + bilingual voice, shown in a desktop OpenCV window | `python smart_glasses_phone_fixed.py`, **or** double-click `InzoziGlasses.exe` if you have the built package | YOLOv8n, `face_recognition`/dlib, DeepFace — all running locally, no cloud calls |
| **B. Browser web app** | A Flask server (`app.py`) + a mobile-friendly web page. Uses your laptop's or phone's own browser camera | `python app.py`, then open the page in a browser | TensorFlow.js (COCO-SSD) client-side for objects + `face_recognition` on the Flask backend for faces |

**Two things to fix before Option B is fully functional** (see [Option B](#running-the-browser-web-app-option-b) for details):
1. `app.py`'s `/` route currently serves `templates/index.html`, which draws face/object boxes with placeholder `Math.random()` logic instead of real detections. `templates/glasses.html` is the page that actually calls the working backend — change the route to serve that instead.
2. `index.html` also calls `/api/voice` and `/api/context`, which don't exist in `app.py` (harmless — they just fail silently).

### Application Package
If a pre-built `InzoziGlasses.exe` is included in your copy of this repo (built via `build_exe.bat` / `smart_glasses.spec`), you can run the full standalone hardware app by double-clicking it — no Python install required. Keep `known_faces/` and `yolov8n.pt` in the same folder as the `.exe`; they're loaded from disk at runtime, not bundled inside it.

---

## How to Use

**Option A — standalone app / .exe:**
1. Choose a language (English or Kinyarwanda) when prompted
2. Enter your phone's IP Webcam address (or leave blank to use your laptop's built-in webcam)
3. Optionally enter an Arduino COM port for distance alerts
4. The video window opens — known faces are named aloud, unknown faces are flagged, objects and scene type are announced, use the on-screen key controls to toggle features live

**Option B — browser app:**
1. Start `app.py`, open the page in a browser, grant camera permission
2. Point the camera at people/objects — face names, positions ("slightly left," "directly ahead," etc.) and object detections appear and are spoken, in whichever language is selected

### Technology Stack
- **Backend:** Python, Flask, Flask-CORS
- **Computer Vision / ML:** OpenCV, Ultralytics YOLOv8n, `face_recognition` (dlib), DeepFace
- **Frontend (web app):** HTML5, CSS3, JavaScript, TensorFlow.js (COCO-SSD), Web Speech API
- **Hardware:** Arduino (HC-SR04 ultrasonic sensor + vibration motor) over serial, Android phone as an IP camera via the IP Webcam app
- **Voice:** Windows PowerShell SAPI (standalone app, Kinyarwanda) / Web Speech API (browser app, both languages)

### Project Structure

```
inzozi_glasses_complete_project/
├── app.py                          # Flask web app (Option B) — face recognition + position API
├── smart_glasses_phone_fixed.py    # Standalone hardware app (Option A) — phone camera +
│                                    #   Arduino + face/object/emotion/scene detection
├── smart_glasses_arduino.ino/      # Arduino firmware: ultrasonic sensor + vibration alerts
├── test_smart_glasses.py           # Tests app.py's Flask API (console output only)
├── test_suite.py                   # Tests smart_glasses_phone_fixed.py's components on real
│                                    #   known_faces/ photos; writes test_results/report.json + .md
├── test_camera.py                  # Standalone webcam diagnostic tool (not part of the app)
├── test_connection.py              # Standalone Arduino serial diagnostic (hardcoded to COM9)
├── test_app.py                     # Duplicate of test_smart_glasses.py (identical content)
├── known_faces/                    # One photo per registered person (name.jpg/.jpeg/.png)
├── models/                         # Model artifacts
├── templates/
│   ├── index.html                  # Older prototype page — partly simulated detections
│   └── glasses.html                # Real, backend-wired page — use this one
├── static/                         # Static assets served by Flask
├── requirements.txt                # Full dependency set (standalone app)
├── requirements_phone.txt          # Lighter dependency set (web app only)
├── requirements_test.txt           # Minimum needed to run test_smart_glasses.py
├── build_exe.bat / smart_glasses.spec  # PyInstaller build config for the .exe
├── fix_com_port.py                 # Arduino COM port helper
├── yolov8n.pt                      # YOLO weights (already included, no download needed)
├── test_results/                   # Test output, if generated by a test run
├── README.md
└── ... (setup/notebook helpers: install_requirements.py, get-pip.py, Initial_Inzozi_Setup.ipynb)
```

---

## Running the Standalone Hardware App (Option A)

This is the full-feature system: face recognition + unknown-face alerts + YOLO object detection + emotion detection + scene (indoor/outdoor) recognition + bilingual voice + optional Arduino distance alerts, all in one OpenCV window.

### Prerequisites
- **Python 3.10 recommended** (3.9–3.11 should also work — this is the range `dlib`/`face_recognition` wheels are most reliable in)
- Windows, macOS, or Linux (developed and tested on Windows)
- An Android phone with the **IP Webcam** app (free, Play Store) for the camera feed
- *(Optional)* An Arduino with an ultrasonic distance sensor (HC-SR04 or similar) flashed with `smart_glasses_arduino.ino`, sending serial lines like `DISTANCE:45`
- A working speaker/audio output for voice alerts

If you don't have the phone or Arduino connected, the app still runs: it automatically falls back to your laptop's built-in webcam, and distance alerts are simply skipped if no Arduino is found.

### Installation

```bash
python -m venv smartglasses_env

# Windows
smartglasses_env\Scripts\activate
# macOS/Linux
source smartglasses_env/bin/activate

pip install -r requirements.txt
```

> `face-recognition` depends on `dlib`, which needs a C++ compiler to build from source unless a prebuilt wheel matches your Python/OS. On Windows, installing **Visual Studio Build Tools** (C++ workload) is usually required — `cmake` alone isn't enough. On macOS, run `brew install cmake` first. On Linux, `sudo apt install cmake build-essential`.
>
> `torch==2.0.1`/`torchvision==0.15.2` and `ultralytics==8.0.196` are pinned together — don't upgrade one without the other. `tensorflow==2.13.0` (for DeepFace) requires Python ≤3.11.

**Add known faces:** put one clear, front-facing photo per person into `known_faces/`, named after that person (e.g. `known_faces/Angelo.jpeg`). The filename (minus extension) becomes the name the app announces.

**Set up the phone camera:**
- Install **IP Webcam** on your Android phone
- Open the app, scroll down, tap **Start server**
- Note the IP address shown (e.g. `192.168.1.65`) — you'll enter this when running the app
- Make sure your phone and computer are on the **same Wi-Fi network**

**yolov8n.pt:** loaded via the relative path `"yolov8n.pt"`, so run the script from the project root folder where it lives (it's already included, no download needed).

### Run it

```bash
python smart_glasses_phone_fixed.py
```

You'll be prompted for:
1. **Language** — `1` for English, `2` for Kinyarwanda (Kinyarwanda speech uses Windows PowerShell SAPI, so that voice path is Windows-only)
2. **Phone IP address** — from the IP Webcam app (leave blank to use the hardcoded default, or if unreachable it falls back to your built-in webcam)
3. **Arduino COM port** — leave blank to skip if you don't have one connected
4. **Which ML features to enable** — Object Detection, Emotion Detection (both default to yes)

### Controls (video window must be focused)

| Key | Action |
|---|---|
| `Q` | Quit |
| `V` | Toggle voice on/off |
| `L` | Switch language (English ↔ Kinyarwanda) |
| `R` | Reload known faces from `known_faces/` |
| `M` | Toggle all ML features on/off |
| `O` | Toggle object detection on/off |
| `E` | Toggle emotion detection on/off |

### If your video looks sideways
Some phones stream video in landscape even when held upright. Open `smart_glasses_phone_fixed.py`, find `FRAME_ROTATION` near the top of the `PhoneCamera` class, and try `cv2.ROTATE_90_CLOCKWISE`, `cv2.ROTATE_180`, or `None` instead of the default.

### Building the .exe
`build_exe.bat` and `smart_glasses.spec` are PyInstaller config targeting `smart_glasses_phone_fixed.py`. Run `build_exe.bat`; the result lands in `dist/`. Keep `known_faces/` and `yolov8n.pt` next to the `.exe`.

---

## Running the Browser Web App (Option B)

```bash
python app.py
```

`app.py` runs with `app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)` — bound to all network interfaces on port 5000, reachable from other devices on your Wi-Fi. It auto-creates `templates/`, `static/`, and `known_faces/` if missing, and prints the known faces it loaded on startup.

- **On the same laptop:** open `http://127.0.0.1:5000` in Chrome/Edge.
- **On a phone:** find your laptop's local IP (`ipconfig` / `ifconfig` / `ip a`), make sure it's on the same Wi-Fi, and open `http://<your-laptop-ip>:5000`.
  - ⚠️ Mobile browsers generally only allow camera access on `https://` or `localhost` — plain `http://192.168.x.x:5000` from another device is usually blocked. Use ngrok (below) to get an `https://` URL.
- Grant camera (and microphone, for voice commands) permission when prompted.

**Make the demo actually functional:** by default `app.py` serves `index.html`, which draws placeholder/random face and object boxes rather than real detections. Change the index route to serve the real, backend-wired page instead:

```python
@app.route('/')
def index():
    return render_template('glasses.html')   # was 'index.html'
```

(Or add a second route, e.g. `@app.route('/glasses')`, to keep both pages available.)

### Exposing it publicly with ngrok
`ngrok-v3-stable-windows-amd64.zip` is included so the local Flask server can be tunneled to a public HTTPS URL — this is what makes phone camera access reliably work. Unzip it, run `app.py` in one terminal, then in another:

```bash
ngrok http 5000
```

Open the `https://...ngrok...` URL it prints on your phone. Note: `app.py` prints a hardcoded `https://spotless-creme-expansive.ngrok-free.dev` on startup — that's a stale leftover from a previous session and won't route to your machine. Use whatever URL **your own** `ngrok http 5000` prints instead (free ngrok URLs are randomly generated per run unless you have a paid reserved domain).

### Lighter install for web-app-only use
If you only want Option B, `requirements_phone.txt` is a smaller dependency set (Flask, Flask-CORS, `face-recognition`, OpenCV, NumPy, Pillow) that skips YOLO/DeepFace/TensorFlow, since object detection runs client-side in the browser for this option.

---

## Arduino Distance Sensor (Optional, for Option A)

`smart_glasses_arduino.ino` drives an HC-SR04 ultrasonic sensor and a vibration motor over serial at **9600 baud**.

| Component | Arduino pin |
|---|---|
| Ultrasonic TRIG | 10 |
| Ultrasonic ECHO | 11 |
| Vibration motor | 6 |

On startup it prints `ARDUINO_READY`, `SMART_GLASSES: System Ready`, `DISTANCE_SENSOR: Active`, then streams `DISTANCE:<cm>` lines continuously plus onboard alert lines (`ALERT:CRITICAL_DANGER`, etc.) that only drive its own vibration — Python only parses the `DISTANCE:` value. Ultrasonic readings out of range come back as `-1` and are treated as "no reading," not an error.

**Known mismatch:** the Arduino vibrates at 20/40/70/120 cm thresholds, while Python's spoken alert only triggers under 50 cm — the glasses may vibrate before they speak. Adjust one or the other if you want them aligned.

Flash the sketch with the Arduino IDE, find its COM port, and enter it when `smart_glasses_phone_fixed.py` asks. `fix_com_port.py` in this repo looks like a helper for identifying/fixing the COM port on Windows if you're not sure which one to use.

---

## Testing

There are two real test suites plus two standalone diagnostic scripts. Run whichever matches what you're testing.

### `test_smart_glasses.py` — tests the Flask web app's API (Option B)

```bash
pip install -r requirements_test.txt
python test_smart_glasses.py
```

This imports `app`, `load_known_faces`, `get_position`, `known_face_names`, `KNOWN_FACES_DIR` directly from `app.py`, so `app.py` and its `known_faces/` folder must be present. It covers:

- `/api/recognize_face` — valid image, missing image, empty image, Kinyarwanda `language` param
- `/api/object_position` — English and Kinyarwanda position labels, missing-data defaults
- `/api/status` and its CORS header
- Static file serving and the `/` index route
- `load_known_faces()` and the `known_faces/` directory contents
- 404 handling and malformed-JSON handling
- Response time of `/api/recognize_face` (must be under 2 seconds)

This file does **not** write `test_results/report.json` or `report.md` — results just print to the console.

### `test_suite.py` — tests the standalone hardware app's components (Option A), writes a report

```bash
python test_suite.py
```

This is the suite that actually matches the "real measurement or honestly-labeled SKIP" testing philosophy from the original project description. It imports `smart_glasses_phone_fixed.py` directly and runs 9 real checks against your actual `known_faces/` photos and libraries — nothing here is a randomly generated pass:

| Test | What it actually does |
|---|---|
| **Face recognition** | Runs real face detection + encoding on every photo in `known_faces/`, reports the actual detection rate |
| **Object detection** | Loads YOLOv8n and runs real inference on real photos from `known_faces/`, reports the actual object classes/confidences detected |
| **Emotion detection** | Runs DeepFace on real photos from `known_faces/`, reports the actual dominant emotion and confidence |
| **Scene recognition** | Runs the real `SceneRecognizer` class on real photos, reports the actual Indoor/Outdoor/Unknown classification |
| **Arduino serial parsing** | Regression tests using exact corrupted/edge-case lines captured from real field logs (mid-session resets, a truncated read, an out-of-range `-1` reading), confirming each is handled without corrupting the distance value |
| **Voice engine logic** | Tests the real `VoiceEngine` class's cooldown/force/queue-overflow behavior with a mocked TTS backend (verifies queueing logic only — doesn't confirm actual audio playback) |
| **Frame rotation fix** | Regression test reproducing the exact 810×1440 landscape-shaped frame logged from a real device, confirming the configured `FRAME_ROTATION` restores it to portrait |
| **Performance (FPS)** | Measures real camera frame rate if a camera is attached; honestly skipped, not faked, if none is available |
| **Bilingual support** | Inspects the actual source code to confirm a Kinyarwanda message branch exists in the distance-alert code |

Results are written to `test_results/report.json` and `test_results/report.md` after every run — these are the files to attach as evidence for a "Testing Results" write-up.

> ⚠️ **Likely bug to fix:** `test_arduino_parsing()` calls `reader.current_distance` and `reader.process_message(...)`, but `reader` is never assigned anywhere in the file (there's no `reader = app.ArduinoReader(...)` line before it's used). As written, this test will raise `NameError: name 'reader' is not defined` rather than actually testing anything. Add an `ArduinoReader` instance (e.g. `reader = app.ArduinoReader(port=None)` or similar, avoiding an attempt to open a real serial port) near the top of that function to fix it.

### `test_camera.py` — standalone webcam diagnostic (not part of the app itself)

```bash
python test_camera.py
```

Scans camera indices 0–4, then tries several backend/resolution combinations (DirectShow, MSMF, auto) via `cv2.VideoCapture`, briefly previewing each in a window. Useful when the standalone app can't find your webcam — prints troubleshooting tips (run as admin, close other camera apps, check Windows privacy settings, try other USB ports, update drivers) at the end. Windows-oriented (`cv2.CAP_DSHOW`/`cv2.CAP_MSMF`), so less relevant on macOS/Linux.

### `test_connection.py` — standalone Arduino serial diagnostic (not part of the app itself)

```bash
python test_connection.py
```

Lists all available COM ports, then attempts to open a connection on **`COM9` specifically (hardcoded)** at 9600 baud, sends a `TEST\n` command, and listens for 5 seconds. If your Arduino is on a different port, edit the `'COM9'` string in the script before running — it won't auto-detect. Prints troubleshooting tips if the connection fails (close Arduino IDE, run as admin, check the cable/port).

### `test_app.py`
This is a duplicate of `test_smart_glasses.py` — character-for-character identical content (same Flask API tests: `/api/recognize_face`, `/api/object_position`, `/api/status`, static files, `load_known_faces()`, error handling, response time). Running either gives you the same result; it's most likely a leftover backup/copy from development rather than a distinct test file. Safe to delete one of the two, or keep both if you want a spare.

---

## Known Limitations

- Face recognition needs a clear, upright, well-lit face — extreme angles or low light reduce accuracy.
- Arduino ultrasonic sensors report `-1` when out of range; this is treated as "no reading," not an error — but its vibration thresholds (20/40/70/120 cm) don't match Python's 50 cm spoken-alert threshold.
- Running all ML features at once (face + object + emotion + scene) on a low-end laptop CPU may reduce frame rate.
- Voice output speaks messages one at a time in the order detected — if many things are detected within the same second, audio may briefly trail behind real time.
- `app.py`'s `/` route serves `index.html` by default, which shows partly-simulated (random) face/object results and calls two endpoints (`/api/voice`, `/api/context`) that don't exist in `app.py` — see [Option B](#running-the-browser-web-app-option-b) for the one-line fix.
- `app.py` prints a stale, hardcoded ngrok URL on startup that won't work for you — use your own `ngrok http 5000` output instead.
- Default phone IP (`192.168.2.102`) and default Arduino COM port (inconsistent between `COM12` and `COM9` in different parts of the code) are hardcoded — just type your actual values when prompted.
- `test_suite.py`'s `test_arduino_parsing()` references an undefined `reader` variable — it will raise `NameError` as currently written rather than actually testing Arduino parsing. See the [Testing](#testing) section for the fix.
- `test_connection.py` is hardcoded to `COM9` and won't auto-detect your Arduino's actual port — edit the script if yours is different.

## Recommendations for Future Work

- Add on-device caching of face encodings so `known_faces/` doesn't need to be re-processed on every restart
- Reconcile the Arduino vibration thresholds with the Python spoken-alert threshold
- Explore a lighter-weight emotion model to reduce CPU load
- Consolidate the multiple `smart_glasses_*.py` variants and test scripts into one maintained entry point each — `test_app.py` in particular is a byte-for-byte duplicate of `test_smart_glasses.py` and can be removed
- Package the hardware app as a mobile app instead of a phone-streams-to-laptop architecture, removing the Wi-Fi dependency
- Add haptic (vibration) feedback synced with the Python voice alerts, not just the Arduino's independent pattern
