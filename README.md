# 🥽 Inzozi Glasses

## Bilingual AI-Powered Smart Glass System for Visually Impaired Users in Rwanda

### Project Overview
Inzozi Glasses (meaning "Dreams" in Kinyarwanda) is an offline wearable smart system that helps visually impaired users navigate indoors, recognize faces, detect emotions, and receive voice guidance in both Kinyarwanda and English.

### Features
-  **Object Detection (YOLOv8n)** - Detects 20+ indoor objects
-  **Room Classification** - Identifies 8 room types
-  **Face Recognition (DeepFace)** - Recognizes registered people
-  **Emotion Detection (CNN-10)** - Detects 7 emotions
-  **RL Navigation (Q-Learning)** - Turn-by-turn directions
-  **Bilingual Voice** - Kinyarwanda + English text-to-speech

### Live Demo
https://drive.google.com/file/d/1wEqMSUo27A3i6y9A18dbjFsulxuEa64-/view?usp=drive_link

### Final Product Demo 
[https://drive.google.com/file/d/1mpUiJL8WEMc0P5mWOZPh33JizW_letGI/view?usp=](https://drive.google.com/file/d/1mpUiJL8WEMc0P5mWOZPh33JizW_letGI/view?usp=drive_link)

### Application Package 
RUN the app by clicking "InzoziGlasses.exe" file

Open `index.html` in any modern browser to see the complete simulation.

### How to Use
1. Select different rooms → See detected objects
2. Select people → Face + emotion recognition activates
3. Set a destination → Navigation directions appear
4. Switch language → Everything changes to Kinyarwanda
5. Click "SPEAK" → Hear voice output

### Technology Stack
- Frontend: HTML5, CSS3, JavaScript
- AI Models: CNN-10, YOLOv8n, DeepFace, Q-Learning
- Voice: Web Speech API (Kinyarwanda + English)

### Project Structure

```
inzozi_glasses_complete_project/
├── index.html                      # Browser-based simulation/demo (see "Live Demo" above)
├── static/                          # Simulation assets, proposal figures
│   ├── fig1_at_coverage.png
│   ├── fig2_benefit_by_region.png
│   ├── fig3_correlation.png
│   ├── fig4_confusion_matrix.png
│   └── fig5_feature_importance.png
├── templates/
│   └── index.html
├── app.py                          # Flask app serving the simulation
├── smart_glasses_phone_fixed.py    # Real hardware application: phone camera +
│                                    #   Arduino + face/object/emotion/scene detection
├── test_smart_glasses.py           # Automated test suite for the hardware app
├── known_faces/                    # One photo per registered person (name.jpg)
├── models/                         # Trained model artifacts (label_encoders.pkl, etc.)
├── requirements.txt                # Python dependencies
├── test_results/                   # Auto-generated after running tests
│   ├── report.json
│   └── report.md
└── README.md
```

---

## Running the Real Hardware System

The browser demo above is a simulation of the concept. The actual wearable
system — phone camera, Arduino distance sensor, and live ML inference — runs
via `smart_glasses_phone_fixed.py`. This section covers installing and
running that real system.

### Prerequisites

- **Python 3.9–3.11** (3.10 recommended — `dlib`/`face_recognition` wheels are most reliable here)
- **Windows, macOS, or Linux** (developed and tested on Windows)
- An Android phone with the **IP Webcam** app (free, Play Store) for the camera feed
- *(Optional)* An Arduino with an ultrasonic distance sensor (HC-SR04 or similar), sending serial lines like `DISTANCE:45`
- A working speaker/audio output for voice alerts

If you don't have the phone or Arduino connected, the app still runs: it
automatically falls back to your laptop's built-in webcam, and distance
alerts are simply skipped if no Arduino is found.

### Installation

1. **Create and activate a virtual environment:**

   ```bash
   python -m venv smartglasses_env

   # Windows
   smartglasses_env\Scripts\activate

   # macOS/Linux
   source smartglasses_env/bin/activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   > `face-recognition` depends on `dlib`, which needs a C++ compiler to
   > build from source. On Windows, installing **Visual Studio Build Tools**
   > is usually required (the `cmake` package alone isn't enough on its own).
   > On macOS, run `brew install cmake` first. On Linux,
   > `sudo apt install cmake build-essential`.

3. **Add known faces:** put one clear, front-facing photo per person into
   `known_faces/`, named after that person (e.g. `known_faces/Angelo.jpg`).
   The filename (minus extension) becomes the name the app announces.

4. **Set up the phone camera:**
   - Install **IP Webcam** on your Android phone
   - Open the app, scroll down, tap **Start server**
   - Note the IP address shown (e.g. `192.168.1.65`) — you'll enter this when running the app
   - Make sure your phone and computer are on the **same Wi-Fi network**

5. *(Optional)* **Set up Arduino:** flash your Arduino with firmware that
   prints a line like `DISTANCE:<value in cm>` over serial at 9600 baud.
   Note which COM port (Windows) or `/dev/tty*` (macOS/Linux) it connects on.

### Run it

```bash
python smart_glasses_phone_fixed.py
```

You'll be prompted for:

1. **Language** — English or Kinyarwanda
2. **Phone IP address** — from the IP Webcam app (leave blank to use the default, or if unreachable it falls back to your built-in webcam)
3. **Arduino COM port** — leave blank to skip if you don't have one connected
4. **Which ML features to enable** — Object Detection, Emotion Detection (both default to yes)

### Controls (while the video window is focused)

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

Some phones stream video in landscape even when held upright, so faces come
out rotated. If that happens, open `smart_glasses_phone_fixed.py`, find
`FRAME_ROTATION` near the top of the `PhoneCamera` class, and try
`cv2.ROTATE_90_CLOCKWISE`, `cv2.ROTATE_180`, or `None` instead.

---

## Testing

Run the test suite:

```bash
python test_smart_glasses.py
```

Every result is either a real measurement or an honestly-labeled `SKIP` —
nothing is a randomly generated number dressed up as a pass:

| Test | What it actually does |
|---|---|
| **Face recognition** | Runs real face detection + encoding on every real photo in `known_faces/`, reports the actual detection rate |
| **Object detection** | Runs YOLOv8 inference on real photos from `known_faces/`, reports the actual object classes and confidence scores detected |
| **Emotion detection** | Runs DeepFace on real photos from `known_faces/`, reports the actual dominant emotion and confidence |
| **Scene recognition** | Runs the real `SceneRecognizer` class on real photos, reports the actual Indoor/Outdoor/Unknown classification |
| **Arduino serial parsing** | Regression tests using the exact corrupted lines captured from real field logs during development, confirming each is correctly rejected without corrupting the distance value |
| **Voice engine logic** | Tests the real `VoiceEngine` class's cooldown/force/queue-overflow behavior with a mocked TTS backend |
| **Frame rotation fix** | Regression test reproducing a real device's landscape-shaped frame, confirming the configured rotation correctly restores it to portrait |
| **Performance (FPS)** | Measures a real camera frame rate if a camera is attached; skipped, not faked, if no camera is available |
| **Bilingual support** | Verifies by inspecting the actual source code that the Kinyarwanda message branch exists |

Results are written to `test_results/report.json` and `test_results/report.md`
after every run — these are the screenshots/evidence to attach for the
"Testing Results" submission requirement.

---

## Known Limitations

- Face recognition needs a clear, upright, well-lit face — extreme angles or low light reduce accuracy
- Arduino ultrasonic sensors report `-1` or similar when out of range; this is treated as "no reading," not an error
- Running all ML features at once (face + object + emotion + scene) on a low-end laptop CPU may reduce frame rate
- Voice output speaks messages one at a time in the order detected — if many things are detected within the same second, audio may briefly trail behind real time
- The browser simulation (`index.html`) illustrates the concept and UX; the live accuracy/performance numbers come from the real hardware app and its test suite, not the simulation

## Recommendations for Future Work

- Add on-device caching of face encodings so `known_faces/` doesn't need to be re-processed on every restart
- Explore a lighter-weight emotion model to reduce CPU load
- Package the hardware app as a mobile app instead of a phone-streams-to-laptop architecture, removing the Wi-Fi dependency
- Add haptic (vibration) feedback as a supplement to audio for noisy environments
