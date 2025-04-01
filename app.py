from flask import Flask, request, jsonify, send_from_directory, url_for, render_template
from flask_cors import CORS
from modules import tts
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
import random
import pyttsx3
import logging
from logging.handlers import RotatingFileHandler

#✅ Load environment variables
load_dotenv()

#✅ Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#✅ ====================== TTS CONFIGURATION ======================
VOICE_OPTIONS = {
    # Basic Voices (pyttsx3)
    'basic': [
        {'id': 'basic-female-1', 'name': 'Basic Female 1', 'lang': 'en', 'service': 'system', 'gender': 'female'},
        {'id': 'basic-male-1', 'name': 'Basic Male 1', 'lang': 'en', 'service': 'system', 'gender': 'male'},
    ],
    
    # Normal Voices (gTTS)
    'normal': [
        # English
        {'id': 'en-female', 'name': 'English Female', 'lang': 'en', 'service': 'gtts', 'gender': 'female'},
        {'id': 'en-male', 'name': 'English Male', 'lang': 'en', 'tld': 'com.au', 'service': 'gtts', 'gender': 'male'},
        {'id': 'uk-female', 'name': 'British Female', 'lang': 'en', 'tld': 'co.uk', 'service': 'gtts', 'gender': 'female'},
        {'id': 'au-female', 'name': 'Australian Female', 'lang': 'en', 'tld': 'com.au', 'service': 'gtts', 'gender': 'female'},
        
        # Hindi
        {'id': 'hi-female-1', 'name': 'Hindi Female 1', 'lang': 'hi', 'service': 'gtts', 'gender': 'female'},
        {'id': 'hi-female-2', 'name': 'Hindi Female 2', 'lang': 'hi', 'tld': 'co.in', 'service': 'gtts', 'gender': 'female'},
        {'id': 'hi-male-1', 'name': 'Hindi Male 1', 'lang': 'hi', 'service': 'gtts', 'gender': 'male'},
        {'id': 'hi-male-2', 'name': 'Hindi Male 2', 'lang': 'hi', 'tld': 'co.in', 'service': 'gtts', 'gender': 'male'},
        
        # Spanish
        {'id': 'es-female', 'name': 'Spanish Female', 'lang': 'es', 'service': 'gtts', 'gender': 'female'},
        {'id': 'es-male', 'name': 'Spanish Male', 'lang': 'es', 'tld': 'com.mx', 'service': 'gtts', 'gender': 'male'},
    ],
    
    # Advanced Voices (ElevenLabs)
    'advanced': [
        {'id': '21m00Tcm4TlvDq8ikWAM', 'name': 'Premium Female 1', 'service': 'elevenlabs', 'gender': 'female'},
        {'id': '29vD33N1CtxCmqQRPOHJ', 'name': 'Premium Male 1', 'service': 'elevenlabs', 'gender': 'male'},
        {'id': 'AZnzlk1XvdvUeBnXmlld', 'name': 'Premium Female 2', 'service': 'elevenlabs', 'gender': 'female'},
        {'id': 'EXAVITQu4vr4xnSDxMaL', 'name': 'Premium Female 3', 'service': 'elevenlabs', 'gender': 'female'},
    ]
}

# Initialize basic voices from system
try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    basic_voices = [
        {'id': f'basic-female-1', 'name': 'Basic Female', 'service': 'system', 'gender': 'female'},
        {'id': f'basic-male-1', 'name': 'Basic Male', 'service': 'system', 'gender': 'male'}
    ]
    VOICE_OPTIONS['basic'] = basic_voices
    engine = None
except Exception as e:
    logger.warning(f"Could not initialize pyttsx3: {str(e)}")

#✅ ====================== FLASK APP SETUP ======================
app = Flask(__name__)
CORS(app)

#✅ API Keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
STABLEHORDE_API_KEY = os.getenv("STABLEHORDE_API_KEY")

#✅ File System Configuration
UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/output'
TEMP_FOLDER = 'temp'
MODEL_PATH = 'models/wav2lip.pth'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

#✅ Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs('models', exist_ok=True)
os.makedirs('static/audio', exist_ok=True)
os.makedirs('static/images', exist_ok=True)

#✅ ====================== CORE FUNCTIONS ======================
def download_wav2lip_model():
    if os.path.exists(MODEL_PATH):
        logger.info("Wav2Lip model already exists")
        return MODEL_PATH

    model_url = "https://drive.google.com/uc?id=1DnMDc4SsVtOxMuSU62jRkDIS1CqRZ3AS"
    logger.info("Downloading Wav2Lip model...")
    
    try:
        gdown.download(model_url, MODEL_PATH, quiet=False)
        logger.info("Wav2Lip model downloaded successfully")
        return MODEL_PATH
    except Exception as e:
        logger.error(f"Failed to download model: {str(e)}")
        raise

def save_image_bytes(image_bytes):
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"image_{timestamp}.png"
        save_path = f"static/images/{filename}"
        
        with open(save_path, "wb") as f:
            f.write(image_bytes)
        
        return {"status": "success", "image_path": save_path, "image_url": f"/static/images/{filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def download_image(image_url):
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"image_{timestamp}.png"
        save_path = f"static/images/{filename}"
        
        img_data = requests.get(image_url).content
        with open(save_path, "wb") as f:
            f.write(img_data)
        
        return {"status": "success", "image_path": save_path, "image_url": f"/static/images/{filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def generate_placeholder_image(prompt):
    try:
        width, height = 1024, 1024
        img = Image.new("RGB", (width, height), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)
        
        font_size = 40
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        text = f"Image for: {prompt}"
        text_width, text_height = draw.textsize(text, font=font)
        draw.text(((width - text_width) / 2, (height - text_height) / 2), text, fill="black", font=font)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"placeholder_{timestamp}.png"
        save_path = f"static/images/{filename}"
        img.save(save_path)
        
        return {"status": "success", "image_path": save_path, "image_url": f"/static/images/{filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def generate_image(prompt, resolution="1024x1024"):
    VALID_RESOLUTIONS = ["256x256", "512x512", "1024x1024"]
    if resolution not in VALID_RESOLUTIONS:
        resolution = "1024x1024"

    try:
        #✅ Try OpenAI API
        if OPENAI_API_KEY:
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "prompt": prompt,
                "n": 1,
                "size": resolution,
                "response_format": "url"
            }
            response = requests.post("https://api.openai.com/v1/images/generations", json=payload, headers=headers)
            
            if response.status_code == 200:
                return download_image(response.json()["data"][0]["url"])
            logger.info("OpenAI API failed, switching to Hugging Face...")

        #✅ Try Hugging Face API
        if HUGGINGFACE_API_KEY:
            headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
            payload = {"inputs": prompt}
            response = requests.post(
                "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                return save_image_bytes(response.content)
            logger.info("Hugging Face API failed, switching to Stable Horde...")

        #✅ Try Stable Horde
        if STABLEHORDE_API_KEY:
            headers = {"apikey": STABLEHORDE_API_KEY}
            payload = {
                "prompt": prompt,
                "params": {
                    "width": int(resolution.split('x')[0]),
                    "height": int(resolution.split('x')[1]),
                    "steps": 30
                }
            }
            response = requests.post("https://stablehorde.net/api/v1/generate", json=payload, headers=headers)
            
            if response.status_code == 200:
                return download_image(response.json().get("image_url"))
            logger.info("Stable Horde API failed, using placeholder...")

        #✅ Final fallback
        return generate_placeholder_image(prompt)
    
    except Exception as e:
        logger.error(f"Image generation error: {str(e)}")
        return {"status": "error", "message": str(e)}

#✅ ====================== TTS FUNCTIONS ======================
def generate_with_elevenlabs(text, voice_id):
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        json=payload,
        headers=headers,
        timeout=10
    )
    return response.content if response.status_code == 200 else None

def generate_with_gtts(text, lang='en', tld='com'):
    tts = gTTS(text=text, lang=lang, tld=tld)
    with open('temp_audio.mp3', 'wb') as f:
        tts.write_to_fp(f)
    with open('temp_audio.mp3', 'rb') as f:
        return f.read()

def generate_with_system(text, voice_id):
    engine = pyttsx3.init()
    try:
        voice_index = int(voice_id.split('-')[-1])
        engine.setProperty('voice', engine.getProperty('voices')[voice_index].id)
        engine.save_to_file(text, 'temp_audio.mp3')
        engine.runAndWait()
        with open('temp_audio.mp3', 'rb') as f:
            return f.read()
    finally:
        engine.stop()

#✅ ====================== ROUTES ======================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Server is healthy"})

@app.route('/api/voices', methods=['GET'])
def get_voices():
    """Get all available voice options organized by category"""
    response = {
        'categories': {
            'basic': {
                'name': 'Basic',
                'description': 'Built-in system voices',
                'voices': VOICE_OPTIONS['basic']
            },
            'normal': {
                'name': 'Normal',
                'description': 'Standard quality voices',
                'voices': VOICE_OPTIONS['normal']
            }
        }
    }
    
    if ELEVENLABS_API_KEY:
        response['categories']['advanced'] = {
            'name': 'Advanced',
            'description': 'High-quality premium voices',
            'voices': VOICE_OPTIONS['advanced']
        }
    
    # Add language filters
    response['languages'] = [
        {'code': 'en', 'name': 'English'},
        {'code': 'hi', 'name': 'Hindi'},
        {'code': 'es', 'name': 'Spanish'}
    ]
    
    # Add gender filters
    response['genders'] = [
        {'code': 'female', 'name': 'Female'},
        {'code': 'male', 'name': 'Male'}
    ]
    
    return jsonify(response)

@app.route('/api/generate_tts', methods=['POST'])
def generate_tts():
    """Generate TTS with 16+ voice options"""
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Content-Type must be application/json'}), 400

    data = request.get_json()
    text = data.get('text', '').strip()
    voice_id = data.get('voice_id', 'en-female')

    if not text:
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400
    if len(text) > 5000:
        return jsonify({'status': 'error', 'message': 'Text exceeds 5000 character limit'}), 400

    try:
        # Find the selected voice
        selected_voice = None
        for category in VOICE_OPTIONS.values():
            for voice in category:
                if voice['id'] == voice_id:
                    selected_voice = voice
                    break
        
        if not selected_voice:
            return jsonify({'status': 'error', 'message': 'Invalid voice selection'}), 400

        # Generate audio
        audio_data = None
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"tts_{voice_id}_{timestamp}.mp3"
        file_path = os.path.join("static/audio", filename)

        if selected_voice['service'] == 'elevenlabs' and ELEVENLABS_API_KEY:
            audio_data = generate_with_elevenlabs(text, voice_id)
        elif selected_voice['service'] == 'gtts':
            audio_data = generate_with_gtts(
                text,
                lang=selected_voice.get('lang', 'en'),
                tld=selected_voice.get('tld', 'com')
            )
        elif selected_voice['service'] == 'system':
            audio_data = generate_with_system(text, voice_id)

        # Fallback to default gTTS if primary method fails
        if not audio_data:
            logger.warning(f"Primary TTS failed for voice {voice_id}, using gTTS fallback")
            audio_data = generate_with_gtts(text)

        # Save the audio file
        with open(file_path, 'wb') as f:
            f.write(audio_data)

        return jsonify({
            'status': 'success',
            'audio_url': f'/static/audio/{filename}',
            'voice_used': selected_voice['name']
        })

    except Exception as e:
        logger.error(f"TTS generation error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

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
        return jsonify(result), (200 if result["status"] == "success" else 500)
    except Exception as e:
        logger.error(f"Image generation API error: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

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

        # Validate file types
        if not (audio_file.filename.lower().endswith(('.mp3', '.wav')) and 
                image_file.filename.lower().endswith(('.png', '.jpg', '.jpeg'))):
            return jsonify({'status': 'error', 'message': 'Invalid file types'}), 400

        # Secure filenames
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

#✅ ====================== MAIN ======================
if __name__ == '__main__':
    download_wav2lip_model()
    app.run(host='0.0.0.0', port=5000, threaded=True)