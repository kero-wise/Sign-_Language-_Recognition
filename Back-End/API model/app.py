from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import base64
import os
import pickle
import cv2
import mediapipe as mp
import numpy as np
from deep_translator import GoogleTranslator
from gtts import gTTS

app = Flask(__name__)
CORS(app)


model = pickle.load(open('./model.p', 'rb'))['model']

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5)
labels_dict = {
    0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'J',
    10: 'K', 11: 'L', 12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R', 18: 'S',
    19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X', 24: 'Y', 25: 'Z', 26: 'del',
    27: 'nothing', 28: 'space'
}

LANGUAGE_MAPPING = {
    "Arabic": "ar",
    "Chinese (Simplified)": "zh-CN",
    "English": "en",
    "French": "fr",
    "German": "de",
    "Gujarati": "gu",
    "Hindi": "hi",
    "Italian": "it",
    "Japanese": "ja",
    "Korean": "ko",
    "Russian": "ru",
    "Spanish": "es",
}

@app.route('/api/process-frame', methods=['POST'])
def process_frame():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400

        img_data = base64.b64decode(data['image'].split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'error': 'Failed to decode image'}), 400

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        all_hand_landmarks = []
        prediction = 'nothing'
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                hand_points = [{'x': lm.x, 'y': lm.y} for lm in hand_landmarks.landmark]
                all_hand_landmarks.append(hand_points)

                x_ = [lm.x for lm in hand_landmarks.landmark]
                y_ = [lm.y for lm in hand_landmarks.landmark]
                data_aux = [(lm.x - min(x_), lm.y - min(y_)) for lm in hand_landmarks.landmark]
                data_aux_flat = [coord for pair in data_aux for coord in pair]

                if len(data_aux_flat) == 42:
                    pred = model.predict([np.asarray(data_aux_flat)])
                    prediction = labels_dict[int(pred[0])]
        
        img_shape = [frame.shape[1], frame.shape[0]]
        return jsonify({
            'prediction': prediction, 
            'landmarks': all_hand_landmarks, 
            'img_shape': img_shape
        })
    except Exception as e:
        print(f"Error in process_frame: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/translate-text', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        target_lang = data.get('target_lang', 'Arabic')
        
        if not text:
            return jsonify({'translation': ''})

        target_code = LANGUAGE_MAPPING.get(target_lang, 'en')
        
        print(f"Translating to {target_lang} (code: {target_code})")
        
        try:
            translated = GoogleTranslator(source='auto', target=target_code).translate(text)
            print(f"Translation result: {translated}")
        except Exception as e:
            print(f"Translation API error: {str(e)}")
            translated = text  
        with open('last_translation.txt', 'w', encoding='utf-8') as f:
            f.write(translated)
        with open('target_lang.txt', 'w', encoding='utf-8') as f:
            f.write(target_code)
            
        return jsonify({'translation': translated})
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-audio/<int:dummy>', methods=['GET'])
def get_audio(dummy):
    try:
        if not os.path.exists('last_translation.txt') or not os.path.exists('target_lang.txt'):
            return jsonify({'error': 'No translation found'}), 404
            
        with open('last_translation.txt', 'r', encoding='utf-8') as f:
            text = f.read().strip()
        with open('target_lang.txt', 'r', encoding='utf-8') as f:
            target_lang = f.read().strip()
            
        if not text:
            return jsonify({'error': 'No text to convert to speech'}), 400
            
        tts = gTTS(text=text, lang=target_lang, slow=False)
        tts.save("translated_audio.mp3")
        
        return send_file(
            "translated_audio.mp3",
            mimetype="audio/mp3",
            as_attachment=False,
            download_name="translation.mp3"
        )
    except Exception as e:
        print(f"Audio generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)