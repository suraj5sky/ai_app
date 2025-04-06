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
import signal
import time
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from utils.path_manager import path_manager
from pathlib import Path
import traceback
import subprocess

# Load environment variables
load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")

if not HF_API_KEY:
    raise ValueError("Hugging Face API Key not found! Check .env file.")

# API headers
HEADERS = {
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"

}
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
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

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
    use_openai = data.get("use_openai", False)

    if not prompt:
        return jsonify({"status": "error", "message": "No prompt provided"}), 400

    try:
        # Call updated generate_image
        result = generate_image(
            prompt=prompt,
            resolution=resolution,
            use_openai=use_openai
        )

        response_data = {
            "status": result["status"],
            "image_url": result.get("image_url"),
            "resolution": result.get("resolution"),
            "message": result.get("message", "")
        }

        return jsonify(response_data), (200 if result["status"] == "success" else 400)

    except Exception as e:
        logger.error(f"Full image generation error: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Server Error: {str(e)}"
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
    # Initialize variables for cleanup
    audio_path = None
    media_path = None
    
    try:
        # Validate inputs
        audio_file = request.files.get('audio')
        media_file = request.files.get('media')
        lip_sync = request.form.get('lip_sync', 'false').lower() == 'true'
        media_type = request.form.get('media_type', 'image')  # image or video

        if not audio_file or not media_file:
            return jsonify({'status': 'error', 'message': 'Audio and media file required'}), 400

        # Validate file extensions
        valid_audio = audio_file.filename.lower().endswith(('.mp3', '.wav'))
        valid_media = (
            media_file.filename.lower().endswith(('.png', '.jpg', '.jpeg')) if media_type == 'image'
            else media_file.filename.lower().endswith(('.mp4', '.mov', '.avi'))
        )
        if not (valid_audio and valid_media):
            return jsonify({
                'status': 'error',
                'message': f'Invalid file types. Expected: {"image" if media_type == "image" else "video"} + audio'
            }), 400

        # Generate secure filenames
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        audio_filename = f"audio_{timestamp}{Path(audio_file.filename).suffix}"
        media_filename = f"media_{timestamp}{Path(media_file.filename).suffix}"
        
        # Save files
        upload_dir = Path(app.config['UPLOAD_FOLDER'])
        upload_dir.mkdir(exist_ok=True)
        
        audio_path = upload_dir / secure_filename(audio_filename)
        media_path = upload_dir / secure_filename(media_filename)
        
        audio_file.save(str(audio_path))
        media_file.save(str(media_path))

        # Process based on media type
        output_dir = Path(app.config['OUTPUT_FOLDER'])
        output_dir.mkdir(exist_ok=True)
        output_filename = f"{'lipsync' if lip_sync else 'video'}_{timestamp}.mp4"
        output_path = output_dir / output_filename

        # Process with timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                process_media_with_audio,
                media_path=str(media_path),
                audio_path=str(audio_path),
                output_path=str(output_path),
                lip_sync=lip_sync,
                is_video=(media_type == 'video')
            )
            try:
                result = future.result(timeout=1800)  # 30 minute timeout
                if not output_path.exists() or output_path.stat().st_size < 1024:
                    return jsonify({
                        'status': 'error',
                        'message': 'Output video creation failed'
                    }), 500
                
                return jsonify({
                    'status': 'success',
                    'video_url': url_for('serve_output', filename=output_filename, _external=True),
                    'file_size': output_path.stat().st_size,
                    'duration': get_video_duration(output_path)
                })
                
            except TimeoutError:
                logger.error("Video generation timed out")
                return jsonify({
                    "status": "error",
                    "message": "Processing took too long"
                }), 504

    except Exception as e:
        logger.error(f"Video generation error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            "status": "error",
            "message": str(e) if app.debug else "Video generation failed"
        }), 500
        
    finally:
        # Cleanup
        for file_path in [audio_path, media_path]:
            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove temp file {file_path}: {str(e)}")

def process_media_with_audio(media_path, audio_path, output_path, lip_sync, is_video):
    """Unified media processing function"""
    try:
        if is_video:
            if lip_sync:
                return run_wav2lip(
                    face_path=media_path,
                    audio_path=audio_path,
                    output_path=output_path,
                    is_static=False
                )
            else:
                return merge_audio_with_video(
                    video_path=media_path,
                    audio_path=audio_path,
                    output_path=output_path
                )
        else:
            if lip_sync:
                # First convert image to video
                temp_video = Path(output_path).with_name(f"temp_{Path(output_path).name}")
                if not create_video_from_image(
                    image_path=media_path,
                    audio_path=audio_path,
                    output_path=str(temp_video)
                ):
                    return {'status': 'error', 'message': 'Image to video conversion failed'}
                
                # Then apply Wav2Lip
                result = run_wav2lip(
                    face_path=str(temp_video),
                    audio_path=audio_path,
                    output_path=output_path,
                    is_static=True
                )
                temp_video.unlink(missing_ok=True)
                return result
            else:
                return create_video_from_image(
                    image_path=media_path,
                    audio_path=audio_path,
                    output_path=output_path
                )
    except Exception as e:
        logger.error(f"Media processing failed: {str(e)}\n{traceback.format_exc()}")
        return {'status': 'error', 'message': str(e)}

def run_wav2lip(face_path, audio_path, output_path, is_static=False):
    """Run Wav2Lip with proper arguments"""
    cmd = [
        "python",
        "D:\\Suraj Yadav\\ai_video_creator\\ai_app\\Wav2Lip\\inference.py",
        "--checkpoint_path", "D:\\Suraj Yadav\\ai_video_creator\\ai_app\\models\\wav2lip.pth",
        "--face", face_path,
        "--audio", audio_path,
        "--outfile", output_path,
        "--resize_factor", "1",
        "--fps", "25",
        "--pads", "0", "10", "0", "0",
        "--nosmooth"
    ]
    
    if is_static:
        cmd.extend(["--static", "True"])
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return {'status': 'success'}
    except subprocess.CalledProcessError as e:
        error_msg = f"Wav2Lip failed: {e.stderr}"
        logger.error(error_msg)
        return {'status': 'error', 'message': error_msg}

def create_video_from_image(image_path, audio_path, output_path):
    """Convert image to video with audio"""
    try:
        cmd = [
            "ffmpeg",
            "-loop", "1",
            "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-t", str(get_audio_duration(audio_path)),
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd, check=True)
        return {'status': 'success'}
    except subprocess.CalledProcessError as e:
        error_msg = f"Image to video conversion failed: {str(e)}"
        logger.error(error_msg)
        return {'status': 'error', 'message': error_msg}

def merge_audio_with_video(video_path, audio_path, output_path):
    """Merge audio with existing video"""
    try:
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd, check=True)
        return {'status': 'success'}
    except subprocess.CalledProcessError as e:
        error_msg = f"Audio merge failed: {str(e)}"
        logger.error(error_msg)
        return {'status': 'error', 'message': error_msg}

def get_audio_duration(audio_path):
    """Get audio duration in seconds"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 30.0  # Default duration if can't detect

def get_video_duration(video_path):
    """Get video duration in seconds"""
    try:
        clip = VideoFileClip(str(video_path))
        duration = clip.duration
        clip.close()
        return duration
    except Exception:
        return None

@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/static/output/<path:filename>')
def serve_output(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    download_wav2lip_model()
    app.run(host='0.0.0.0', port=5000, threaded=True)
