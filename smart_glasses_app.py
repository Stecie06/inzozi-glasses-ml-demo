#!/usr/bin/env python3
"""
INZOZI SMART GLASSES - Web Interface Backend
This provides the web interface that works with your smart_glasses_phone_fixed.py
"""

import os
import json
import time
import threading
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)

# ============================================================
# KINYARWANDA TRANSLATIONS
# ============================================================
KINYARWANDA = {
    'person_detected': 'Muntu yagaragaye',
    'unknown_person': 'Muntu utazwi',
    'happy': 'arishimye',
    'sad': 'arababaye',
    'angry': 'yarakaye',
    'surprise': 'atangaye',
    'fear': 'afite ubwoba',
    'disgust': 'arakubita',
    'neutral': 'aratuje',
    'caution': 'Itondere',
    'object': 'ikintu',
    'centimeters': 'santimetero',
    'ahead': 'imbere',
    'outdoor': 'Hanze',
    'indoor': 'Mu nzu',
    'system_ready': 'Sisitemu iteguye',
    'ml_ready': 'Sisitemu ifite ubuhanga bwa machine learning',
    'goodbye': 'Murabeho',
    'left': 'Erekeza ibumoso',
    'right': 'Erekeza iburyo',
    'straight': 'Genda gatoro',
    'stop': 'Hagarara'
}

# ============================================================
# NLP PROCESSOR
# ============================================================

class SmartGlassesNLP:
    def __init__(self):
        self.commands_en = {
            'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon'],
            'status': ['status', 'system status', "what's up"],
            'direction_left': ['turn left', 'go left', 'left'],
            'direction_right': ['turn right', 'go right', 'right'],
            'direction_straight': ['straight', 'go straight', 'forward'],
            'direction_stop': ['stop', 'halt'],
            'object': ['what is that', "what's that", 'identify', 'detect object'],
            'face': ['who is that', 'recognize face', 'who are they'],
            'language_rw': ['kinyarwanda', 'switch to rw'],
            'language_en': ['english', 'switch to en'],
            'help': ['help', 'commands', 'what can you do'],
            'distance': ['distance', 'how far', 'range'],
            'quit': ['quit', 'exit', 'goodbye']
        }
        
        self.commands_rw = {
            'greeting': ['muraho', 'bite', 'mwiriwe', 'amakuru'],
            'status': ['bite', 'status', 'sisitemu'],
            'direction_left': ['erekeza ibumoso', 'genda ibumoso', 'ibumoso'],
            'direction_right': ['erekeza iburyo', 'genda iburyo', 'iburyo'],
            'direction_straight': ['genda gatoro', 'gatoro'],
            'direction_stop': ['hagarara'],
            'object': ['iki ni iki', 'ni iki', 'menya ikintu'],
            'face': ['uyu ni nde', 'menya umuntu', 'ni nde'],
            'language_rw': ['kinyarwanda', 'hindura mu rw'],
            'language_en': ['icongereza', 'hindura mu en'],
            'help': ['ubufasha', 'amateka', 'fasha'],
            'distance': ['intera', 'kure'],
            'quit': ['genda', 'reka', 'murabeho']
        }
        
        self.responses = {
            'en': {
                'greeting': 'Hello! How can I assist you?',
                'status': 'System running. Face recognition and object detection active.',
                'direction_left': 'Turning left',
                'direction_right': 'Turning right',
                'direction_straight': 'Going straight',
                'direction_stop': 'Stopping',
                'object': 'Detecting objects...',
                'face': 'Looking for faces...',
                'language_rw': 'Switched to Kinyarwanda',
                'language_en': 'Switched to English',
                'help': 'Commands: status, direction (left/right/straight/stop), object detection, face recognition, distance, language, quit',
                'distance': 'Checking distance...',
                'quit': 'Goodbye!',
                'unknown': "I didn't understand that. Say 'help' for commands."
            },
            'rw': {
                'greeting': 'Muraho! Nkubafasha iki?',
                'status': 'Sisitemu ikora. Kumenya abantu n\'ibintu birakora.',
                'direction_left': 'Erekeza ibumoso',
                'direction_right': 'Erekeza iburyo',
                'direction_straight': 'Genda gatoro',
                'direction_stop': 'Hagarara',
                'object': 'Ndashakisha ibintu...',
                'face': 'Ndashakisha abantu...',
                'language_rw': 'Ururimi rwahinduwe mu Kinyarwanda',
                'language_en': 'Ururimi rwahinduwe mu Congereza',
                'help': 'Amateka: status, erekeza (ibumoso/iburyo/gatoro/hagarara), menya ikintu, menya umuntu, intera, hindura ururimi',
                'distance': 'Intera ikirangwa...',
                'quit': 'Murabeho!',
                'unknown': 'Simbumvishe. Vuga "ubufasha" kugira ngo ubone amateka.'
            }
        }
    
    def detect_language(self, text):
        text_lower = text.lower()
        rw_indicators = ['muraho', 'bite', 'mwiriwe', 'amakuru', 'genda', 'hagarara', 
                        'intera', 'kure', 'ubufasha', 'kinyarwanda']
        if any(indicator in text_lower for indicator in rw_indicators):
            return 'rw'
        return 'en'
    
    def process_command(self, text):
        text_lower = text.lower().strip()
        language = self.detect_language(text_lower)
        commands = self.commands_rw if language == 'rw' else self.commands_en
        responses = self.responses[language]
        
        for action, patterns in commands.items():
            for pattern in patterns:
                if pattern in text_lower:
                    if action == 'language_rw':
                        return {'action': 'language_switch', 'response': responses['language_rw'], 'language': 'rw'}
                    elif action == 'language_en':
                        return {'action': 'language_switch', 'response': responses['language_en'], 'language': 'en'}
                    else:
                        return {'action': action, 'response': responses.get(action, responses['unknown']), 'language': language}
        
        return {'action': 'unknown', 'response': responses['unknown'], 'language': language}


bridge = SmartGlassesNLP()
current_language = 'en'

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/glasses')
def glasses_index():
    """Serve the smart glasses interface"""
    return render_template('glasses.html')

@app.route('/api/voice', methods=['POST'])
def handle_voice():
    """Handle voice command"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        result = bridge.process_command(text)
        logger.info(f"Voice: '{text}' -> {result['action']}")
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    return jsonify({
        'status': 'running',
        'language': current_language,
        'face_recognition': 'active',
        'object_detection': 'active'
    })

@app.route('/api/language', methods=['POST'])
def set_language():
    """Set language"""
    try:
        data = request.get_json()
        lang = data.get('language', 'en')
        global current_language
        if lang in ['en', 'rw']:
            current_language = lang
            return jsonify({'status': 'success', 'language': lang})
        return jsonify({'error': 'Invalid language'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# ============================================================
# RUN
# ============================================================

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("\n" + "=" * 70)
    print(" INZOZI SMART GLASSES - Web Interface")
    print("=" * 70)
    print(" Features:")
    print("   - Mobile-optimized web interface")
    print("   - Voice commands with NLP")
    print("   - Bilingual (English + Kinyarwanda)")
    print("=" * 70)
    print("\n🌐 Web interface at: http://localhost:5000/glasses")
    print("\n" + "=" * 70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)