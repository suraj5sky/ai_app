from flask import Flask, request, jsonify, send_from_directory, url_for, render_template
from flask_cors import CORS
from modules.image_gen import generate_image
from modules.video_creator import create_video
from modules.lipsync import run_lipsync
from dotenv import load_dotenv
from datetime import datetime
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from werkzeug.utils import secure_filename
import os
import requests
import gdown
import logging
import re
import tempfile
import edge_tts
import asyncio
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=1000000, backupCount=3),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Voice Configuration (Final Structure)
LANGUAGES = ["hindi", "english", "spanish", "french", "arabic", "german", "japanese"]

VOICES = {
    "hindi": [
        {"id": "hi-IN-MadhurNeural", "name": "Surja (Male)", "gender": "male", "service": "edge"},
        {"id": "hi-IN-SwaraNeural", "name": "Riya (Female)", "gender": "female", "service": "edge"},
        {"id": "hi-IN-KedarNeural", "name": "Aditya (Male)", "gender": "male", "service": "edge"},
        {"id": "hi-IN-PoojaNeural", "name": "Priya (Female)", "gender": "female", "service": "edge"}
    ],
    "english": [
        {"id": "en-US-DavisNeural", "name": "Surja (Male)", "gender": "male", "service": "edge"},
        {"id": "en-US-JennyNeural", "name": "Riya (Female)", "gender": "female", "service": "edge"},
        {"id": "en-US-GuyNeural", "name": "Abhi (Male)", "gender": "male", "service": "edge"},
        {"id": "en-US-AriaNeural", "name": "Baba (Female)", "gender": "female", "service": "edge"},
        {"id": "en-US-NancyNeural", "name": "Tanya (Female)", "gender": "female", "service": "edge"}
    ],
    "spanish": [
        {"id": "es-ES-AlvaroNeural", "name": "Carlos (Male)", "gender": "male", "service": "edge"},
        {"id": "es-ES-ElviraNeural", "name": "Sofia (Female)", "gender": "female", "service": "edge"}
    ],
    "french": [
        {"id": "fr-FR-HenriNeural", "name": "Luc (Male)", "gender": "male", "service": "edge"},
        {"id": "fr-FR-DeniseNeural", "name": "Élodie (Female)", "gender": "female", "service": "edge"}
    ],
    "arabic": [
        {"id": "ar-SA-HamedNeural", "name": "Khalid (Male)", "gender": "male", "service": "edge"},
        {"id": "ar-SA-ZariyahNeural", "name": "Layla (Female)", "gender": "female", "service": "edge"}
    ],
    "german": [
        {"id": "de-DE-ConradNeural", "name": "Max (Male)", "gender": "male", "service": "edge"},
        {"id": "de-DE-KatjaNeural", "name": "Anna (Female)", "gender": "female", "service": "edge"}
    ],
    "japanese": [
        {"id": "ja-JP-KeitaNeural", "name": "Haruto (Male)", "gender": "male", "service": "edge"},
        {"id": "ja-JP-NanamiNeural", "name": "Sakura (Female)", "gender": "female", "service": "edge"}
    ]
}

# Language to gTTS code mapping
GTTS_LANG_CODES = {
    "hindi": "hi",
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "arabic": "ar",
    "german": "de",
    "japanese": "ja"
}

# Flask app setup
app = Flask(__name__)
CORS(app)

# File system configuration
UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/output'
TEMP_FOLDER = 'temp'
MODEL_PATH = 'models/wav2lip.pth'
AUDIO_FOLDER = 'static/audio'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs('models', exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs('static/images', exist_ok=True)

def download_wav2lip_model():
    if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 100_000_000:  # ~100MB
        logger.info("Wav2Lip model already exists")
        return MODEL_PATH

    file_id = "1Z6BUbVI0LqIzRrepoo13pflWE_XUXETs"
    model_url = f"https://drive.google.com/uc?id={file_id}"
    
    logger.info("Downloading Wav2Lip model...")
    try:
        gdown.download(model_url, MODEL_PATH, quiet=False)
        
        # Verify download completed
        if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) < 100_000_000:
            raise ValueError("Downloaded file is incomplete or corrupted")
            
        logger.info("Wav2Lip model downloaded successfully")
        return MODEL_PATH
    except Exception as e:
        logger.error(f"Failed to download model: {str(e)}")
        if os.path.exists(MODEL_PATH):  # Clean up partial downloads
            os.remove(MODEL_PATH)
        raise

def save_audio_file(audio_data, voice_id):
    """Save audio file with proper naming"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"tts_{voice_id}_{timestamp}.mp3"
        filepath = os.path.join(AUDIO_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            f.write(audio_data)
        
        return {
            "status": "success",
            "audio_url": f"/static/audio/{filename}",
            "filepath": filepath
        }
    except Exception as e:
        logger.error(f"Error saving audio file: {str(e)}")
        return {"status": "error", "message": str(e)}

async def async_generate_with_edge(text, voice_id):
    """Async Edge-TTS generation"""
    try:
        communicate = edge_tts.Communicate(text, voice_id)
        temp_file = os.path.join(TEMP_FOLDER, f"edge_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3")
        await communicate.save(temp_file)
        return temp_file
    except Exception as e:
        logger.error(f"Edge-TTS generation error: {str(e)}")
        return None

def generate_with_edge(text, voice_id):
    """Synchronous Edge-TTS wrapper"""
    try:
        temp_file = asyncio.run(async_generate_with_edge(text, voice_id))
        if temp_file and os.path.exists(temp_file):
            with open(temp_file, 'rb') as f:
                audio_data = f.read()
            os.remove(temp_file)
            return audio_data
        return None
    except Exception as e:
        logger.error(f"Edge-TTS sync error: {str(e)}")
        return None

def generate_with_gtts(text, lang='en'):
    """gTTS fallback"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            temp_path = tmp_file.name
        
        tts = gTTS(text=text, lang=lang)
        tts.save(temp_path)
        
        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        
        os.remove(temp_path)
        return audio_data
    except Exception as e:
        logger.error(f"gTTS error: {str(e)}")
        return None

@app.route('/api/voices', methods=['GET'])
def get_voices():
    """Return structured voice options"""
    try:
        return jsonify({
            'status': 'success',
            'languages': LANGUAGES,
            'voices': VOICES,
            'max_char_limit': 2000
        })
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/generate_tts', methods=['POST'])
def generate_tts():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    text = data.get('text', '').strip()
    language = data.get('language', '')
    voice_id = data.get('voice_id', '')
    
    if not text or not language or not voice_id:
        return jsonify({'status': 'error', 'message': 'Text, language and voice_id are required'}), 400
    
    if len(text) > 2000:
        return jsonify({
            'status': 'error', 
            'message': 'Text exceeds 2000 character limit',
            'max_limit': 2000
        }), 400

    try:
        # Find the selected voice
        selected_voice = None
        for voice in VOICES.get(language, []):
            if voice['id'] == voice_id:
                selected_voice = voice
                break
        
        if not selected_voice:
            return jsonify({'status': 'error', 'message': 'Invalid voice selection'}), 400

        # Generate audio (Edge-TTS first, gTTS fallback)
        audio_data = generate_with_edge(text, voice_id)
        if not audio_data:
            logger.info(f"Edge-TTS failed, falling back to gTTS")
            lang_code = GTTS_LANG_CODES.get(language, "en")
            audio_data = generate_with_gtts(text, lang=lang_code)
            if audio_data:
                selected_voice['name'] += " (gTTS Fallback)"

        if not audio_data:
            raise Exception("All TTS methods failed")

        # Save and return result
        save_result = save_audio_file(audio_data, voice_id)
        if save_result['status'] != 'success':
            raise Exception(save_result['message'])

        return jsonify({
            'status': 'success',
            'audio_url': save_result['audio_url'],
            'voice_used': selected_voice['name'],
            'language': language,
            'service': selected_voice.get('service', 'gtts')
        })

    except Exception as e:
        logger.error(f"TTS generation error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# [Keep all other existing routes unchanged...]
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Server is healthy"})

@app.route('/api/generate_image', methods=['POST'])
def generate_image_api():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    prompt = data.get("prompt", "").strip()
    resolution = data.get("resolution", "1024x1024")
    
    if not prompt:
        return jsonify({"status": "error", "message": "No prompt provided"}), 400
    
    try:
        result = generate_image(prompt, resolution=resolution)
        
        # Ensure consistent response format
        response_data = {
            "status": result["status"],
            "image_url": result.get("image_url"),  # Frontend looks for this
            "message": result.get("message", "")
        }
        
        return jsonify(response_data), (200 if result["status"] == "success" else 400)
        
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({
            'status': 'success',
            'file_url': url_for('serve_upload', filename=filename)
        })
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'File upload failed'}), 500

@app.route('/api/generate_video', methods=['POST'])
def create_video_api():
    try:
        audio_file = request.files.get('audio')
        image_file = request.files.get('image')
        lip_sync = request.form.get('lip_sync', 'false').lower() == 'true'

        if not audio_file or not image_file:
            return jsonify({'status': 'error', 'message': 'Audio and image required'}), 400

        if not (audio_file.filename.lower().endswith(('.mp3', '.wav')) and 
                image_file.filename.lower().endswith(('.png', '.jpg', '.jpeg'))):
            return jsonify({'status': 'error', 'message': 'Invalid file types'}), 400

        audio_filename = secure_filename(audio_file.filename)
        image_filename = secure_filename(image_file.filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        
        audio_file.save(audio_path)
        image_file.save(image_path)

        output_filename = f"video_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)

        if lip_sync:
            logger.info("Using Wav2Lip for lipsync...")
            success = run_lipsync(
                face_image_path=image_path,
                audio_path=audio_path,
                output_path=output_path,
                wav2lip_model_path=MODEL_PATH
            )
            if not success:
                return jsonify({'status': 'error', 'message': 'Wav2Lip failed'}), 500
        else:
            logger.info("Using basic video generation...")
            result = create_video(image_path, audio_path, output_folder=OUTPUT_FOLDER)
            if result['status'] != 'success':
                return jsonify(result), 500

        return jsonify({
            'status': 'success',
            'video_url': url_for('serve_output', filename=output_filename)
        })

    except Exception as e:
        logger.error(f"Video generation error: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/static/output/<path:filename>')
def serve_output(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    download_wav2lip_model()
    app.run(host='0.0.0.0', port=5000, threaded=True)