from flask import Flask, render_template, request, send_from_directory
import joblib
import numpy as np
import os

app = Flask(__name__)

model = joblib.load('models/model.pkl')
scaler = joblib.load('models/scaler.pkl')
label_encoders = joblib.load('models/label_encoders.pkl')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        region = request.form.get('region')
        income = request.form.get('income')
        rural_urban = request.form.get('rural_urban')
        at_cov = float(request.form.get('at_coverage'))
        internet = float(request.form.get('internet'))
        mobile = float(request.form.get('mobile'))
        edu = int(request.form.get('education'))
        
        region_enc = label_encoders['Region'].transform([region])[0]
        income_enc = label_encoders['Income_Level'].transform([income])[0]
        rural_enc = label_encoders['Rural_Urban'].transform([rural_urban])[0]
        
        features = np.array([[at_cov, internet, mobile, edu, region_enc, income_enc, rural_enc]])
        features_scaled = scaler.transform(features)
        
        pred = model.predict(features_scaled)[0]
        prob = model.predict_proba(features_scaled)[0][1]
        
        result = {
            'benefit': bool(pred),
            'confidence': float(prob),
            'message': 'This population would BENEFIT from Inzozi Glasses!' if pred == 1 else 'This population may not benefit significantly'
        }
        return render_template('index.html', prediction=result)
    except Exception as e:
        return render_template('index.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

print("app.py created!")
