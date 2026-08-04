import os
import json
import logging
import base64
import numpy as np
import cv2
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import face_recognition

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# ============================================================
# LOAD KNOWN FACES
# ============================================================

KNOWN_FACES_DIR = 'known_faces'
known_face_encodings = []
known_face_names = []

def load_known_faces():
    global known_face_encodings, known_face_names
    known_face_encodings = []
    known_face_names = []
    
    if not os.path.exists(KNOWN_FACES_DIR):
        os.makedirs(KNOWN_FACES_DIR)
        return
    
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            name = os.path.splitext(filename)[0]
            try:
                image = face_recognition.load_image_file(os.path.join(KNOWN_FACES_DIR, filename))
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    known_face_names.append(name)
                    logger.info(f" Loaded face: {name}")
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")

load_known_faces()

# ============================================================
# SPATIAL POSITIONING
# ============================================================

def get_position(x, width, language='en'):
    center = width / 2
    left_threshold = center * 0.3
    right_threshold = center * 0.7
    
    if language == 'rw':
        if x < center * 0.1:
            return "kure ibumoso"
        elif x < left_threshold:
            return "ibumoso"
        elif x < center * 0.35:
            return "hagati n'ibumoso"
        elif x < center * 0.65:
            return "hagati"
        elif x < right_threshold:
            return "hagati n'iburyo"
        elif x < center * 0.9:
            return "iburyo"
        else:
            return "kure iburyo"
    else:
        if x < center * 0.1:
            return "far left"
        elif x < left_threshold:
            return "on your left"
        elif x < center * 0.35:
            return "slightly left"
        elif x < center * 0.65:
            return "directly ahead"
        elif x < right_threshold:
            return "slightly right"
        elif x < center * 0.9:
            return "on your right"
        else:
            return "far right"

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/recognize_face', methods=['POST'])
def recognize_face():
    try:
        data = request.get_json()
        image_data = data.get('image', '')
        language = data.get('language', 'en')
        if not image_data:
            return jsonify({'error': 'No image provided'}), 400
        
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        height, width = img.shape[:2]
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_img)
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
        
        results = []
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            name = "Unknown"
            is_known = False
            
            if known_face_encodings:
                distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_idx = np.argmin(distances)
                
                if distances[best_idx] < 0.6:
                    name = known_face_names[best_idx]
                    is_known = True
            
            center_x = (left + right) / 2
            position = get_position(center_x, width, language)
            
            results.append({
                'name': name,
                'is_known': is_known,
                'box': [left, top, right, bottom],
                'x': left,
                'y': top,
                'width': right - left,
                'height': bottom - top,
                'position': position,
                'center_x': center_x
            })
        
        return jsonify({
            'faces': results,
            'known_faces': len(known_face_names),
            'known_names': known_face_names
        })
        
    except Exception as e:
        logger.error(f"Face recognition error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/object_position', methods=['POST'])
def get_object_position():
    try:
        data = request.get_json()
        x = data.get('x', 0)
        width = data.get('width', 640)
        language = data.get('language', 'en')
        position = get_position(x, width, language)
        return jsonify({'position': position})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        'status': 'running',
        'known_faces': len(known_face_names),
        'known_names': known_face_names
    })

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('known_faces', exist_ok=True)
    
    print("\n" + "=" * 70)
    print(" INZOZI SMART GLASSES - VOICE-ONLY SYSTEM")
    print("=" * 70)
    print(f"\n Known faces: {', '.join(known_face_names) if known_face_names else 'None'}")
    print("\n  FULLY VOICE-INTERACTIVE")
    print("   - Language selection by voice")
    print("   - No buttons ever")
    print("\n Server starting...")
    print(" Open on phone: https://spotless-creme-expansive.ngrok-free.dev")
    print("=" * 70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)