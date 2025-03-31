from flask import Flask, request, jsonify, send_from_directory, url_for, render_template
from flask_cors import CORS
from modules import tts
from modules.image_gen import generate_image
from modules.video_creator import create_video
from modules.lipsync import run_lipsync
from dotenv import load_dotenv
from datetime import datetime
import os
import requests
import gdown

# ✅ Load environment variables
load_dotenv()
huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# ✅ Check API Keys
if not huggingface_api_key:
    print("⚠️ Warning: Hugging Face API Key not loaded!")
if not openai_api_key:
    print("ℹ️ Info: OpenAI API Key not loaded (optional)")

# ✅ Flask App Init
app = Flask(__name__)
CORS(app)

# ✅ Folder Config
UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/output'
TEMP_FOLDER = 'temp'
MODEL_PATH = 'models/wav2lip.pth'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs('models', exist_ok=True)

# ✅ Google Drive Model Download (Real Method)
def download_wav2lip_model():
    model_url = "https://drive.google.com/uc?id=1DnMDc4SsVtOxMuSU62jRkDIS1CqRZ3AS"  # Replace with actual Google Drive ID
    model_path = "wav2lip.pth"

    if not os.path.exists(model_path):
        print("Downloading Wav2Lip model...")
        try:
            response = requests.get(model_url, stream=True)
            response.raise_for_status()
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print("✅ Wav2Lip model downloaded successfully!")
        except Exception as e:
            print(f"❌ Failed to download model: {e}")
    else:
        print("✅ Wav2Lip model already exists.")

    return model_path

# ✅ Home Route
@app.route('/')
def home():
    return render_template('index.html')

# ✅ Health Check
@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Server is up and running"})

# ✅ TTS API
MAX_TTS_CHARACTERS = 2000  # Set your preferred limit

@app.route('/api/generate_tts', methods=['POST'])
def generate_tts():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request content-type must be application/json'}), 400

    data = request.get_json()
    text = data.get('text', '')
    lang = data.get('lang', 'en')
    slow = data.get('slow', False)

    # Check character limit
    if len(text) > MAX_TTS_CHARACTERS:
        return jsonify({'error': f'Text too long! Max {MAX_TTS_CHARACTERS} characters allowed.'}), 400
    
    if not text.strip():
        return jsonify({'status': 'error', 'message': 'No text provided'}), 400

    try:
        output_path = tts.generate_tts(text, OUTPUT_FOLDER, lang=lang, slow=slow)
        return jsonify({
            'status': 'success',
            'audio_url': url_for('serve_output', filename=os.path.basename(output_path))
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/generate_tts', methods=['POST'])
def generate_tts():
    text = request.form.get('text', '')
    voice = request.form.get('voice', 'female')  # Default to female voice

    if voice not in ['female', 'male']:
        return jsonify({'error': 'Invalid voice selection!'}), 400

    # Example: Use voice selection in TTS API
    tts_api_url = "YOUR_TTS_API_ENDPOINT"
    payload = {
        'text': text,
        'voice': 'en-US-Wavenet-F' if voice == 'female' else 'en-US-Wavenet-D'
    }

    response = requests.post(tts_api_url, json=payload)

    if response.status_code == 200:
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"tts_{voice}_{timestamp}.mp3"

        # Save with proper name
        with open(f"static/audio/{filename}", "wb") as f:
            f.write(response.content)

        return jsonify({'audio_url': f'/static/audio/{filename}'})
    else:
        return jsonify({'error': 'TTS generation failed'}), 500

# ✅ Image Generator API
@app.route('/api/generate_image', methods=['POST'])
def generate_image_api():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request content-type must be application/json'}), 400

    data = request.get_json()
    prompt = data.get("prompt")
    resolution = data.get("resolution", "1024x1024")  # Default is 1024x1024
    use_openai = data.get("use_openai", False)
    
     image_url = generate_image(prompt, resolution)
    return jsonify({"image_url": image_url})
    
    if not prompt or not prompt.strip():
        return jsonify({"status": "error", "message": "No prompt provided"}), 400

    try:
        result = generate_image(prompt, output_folder=OUTPUT_FOLDER, use_openai=use_openai)
        if result["status"] == "success":
            return jsonify({
                "status": "success",
                "image_path": result.get("image_path"),
                "image_url": result.get("url")
            })
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ Upload API
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part in request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    try:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        file_url = url_for('serve_upload', filename=file.filename, _external=True)
        return jsonify({
            'status': 'success',
            'filename': file.filename,
            'file_path': filepath,
            'file_url': file_url
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ✅ Serve Uploaded Files
@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ✅ Serve Output Files
@app.route('/static/output/<path:filename>')
def serve_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

# ✅ Video Creator API
@app.route('/api/generate_video', methods=['POST'])
def create_video_api():
    try:
        audio_file = request.files.get('audio')
        image_file = request.files.get('image')
        lip_sync = request.form.get('lip_sync', 'false').lower() == 'true'

        if not audio_file or not image_file:
            return jsonify({'status': 'error', 'message': 'Audio and image are required.'}), 400

        audio_path = os.path.join(UPLOAD_FOLDER, audio_file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
        audio_file.save(audio_path)
        image_file.save(image_path)

        output_path = os.path.join(OUTPUT_FOLDER, 'final_video.mp4')

        if lip_sync:
            print("🔁 Using Wav2Lip for lipsync...")
            success = run_lipsync(
                face_image_path=image_path,
                audio_path=audio_path,
                output_path=output_path,
                wav2lip_model_path=MODEL_PATH
            )
            if not success:
                return jsonify({'status': 'error', 'message': 'Wav2Lip failed.'}), 500
        else:
            print("🎬 Using MoviePy for basic video generation...")
            result = create_video(image_path, audio_path, output_folder=OUTPUT_FOLDER)
            if result['status'] != 'success':
                return jsonify(result), 500

        return jsonify({
            'status': 'success',
            'video_path': output_path
        })

    except Exception as e:
        print("❌ Exception in create_video_api:", e)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ✅ Start Flask App (after model download)
if __name__ == '__main__':
    model_path = download_wav2lip_model()  # Ensure Wav2Lip model is downloaded before starting Flask
    app.run(debug=True, host='0.0.0.0', port=5000)

