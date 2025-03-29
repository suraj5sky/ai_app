from flask import Flask, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
from modules import tts
from modules.image_gen import generate_image
from modules.video_creator import create_video
from modules.lipsync import run_lipsync   # ✅ Added Wav2Lip lipsync import
from dotenv import load_dotenv
import os
import requests

# ✅ Load environment variables
load_dotenv()
huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")  # Optional

# 🔐 Check API Key availability
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
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ✅ Home Route
@app.route('/')
def home():
    return jsonify({
        "message": "🎬 Welcome to AI Video Creator Backend (gTTS + Hugging Face + OpenAI Ready)",
        "status": "running"
    })

# ✅ Health Check
@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Server is up and running"})

# ✅ TTS API
@app.route('/api/tts', methods=['POST'])
def generate_tts():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request content-type must be application/json'}), 400

    data = request.get_json()
    text = data.get('text', '')
    lang = data.get('lang', 'en')
    slow = data.get('slow', False)

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

# ✅ Image Generator API
@app.route('/api/generate_image', methods=['POST'])
def generate_image_api():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request content-type must be application/json'}), 400

    data = request.get_json()
    prompt = data.get("prompt")
    use_openai = data.get("use_openai", False)

    if not prompt or not prompt.strip():
        return jsonify({"status": "error", "message": "No prompt provided"}), 400

    print(f"🧠 Generating image for prompt: '{prompt}' | OpenAI: {use_openai}")

    try:
        result = generate_image(prompt, output_folder=OUTPUT_FOLDER, use_openai=use_openai)
        if result["status"] == "success":
            return jsonify({
                "status": "success",
                "image_path": result.get("image_path"),
                "image_url": result.get("url")  # If applicable
            })
        else:
            return jsonify(result), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ✅ Upload API for image/audio files
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

# ✅ Serve uploaded files
@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ✅ Video Creator API with lipsync toggle
@app.route('/api/create_video', methods=['POST'])
def create_video_api():
    try:
        audio_file = request.files.get('audio')
        image_file = request.files.get('image')
        lip_sync = request.form.get('lip_sync', 'false').lower() == 'true'

        if not audio_file or not image_file:
            return jsonify({'status': 'error', 'message': 'Audio and image are required.'}), 400

        # Save uploaded files
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
        audio_file.save(audio_path)
        image_file.save(image_path)

        output_path = os.path.join(app.config['OUTPUT_FOLDER'], 'final_video.mp4')

        if lip_sync:
            print("🔁 Using Wav2Lip for lipsync...")
            success = run_lipsync(
                face_image_path=image_path,
                audio_path=audio_path,
                output_path=output_path,
                wav2lip_model_path="modules/wav2lip.pth"
            )
            if not success:
                return jsonify({'status': 'error', 'message': 'Wav2Lip failed.'}), 500
        else:
            print("🎬 Using MoviePy for basic video generation...")
            result = create_video(image_path, audio_path, output_folder=app.config['OUTPUT_FOLDER'])
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

# ✅ Serve static output files
@app.route('/static/output/<path:filename>')
def serve_output(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

# ✅ Run Flask server
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # 'host' important for cloud platforms

# Upload Wav2Lip file via Google drive or other cloud storage platforms
MODEL_URL = "https://drive.google.com/file/d/1DnMDc4SsVtOxMuSU62jRkDIS1CqRZ3AS/view?usp=sharing"
MODEL_PATH = "models/wav2lip.pth"

def download_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading Wav2Lip model...")
        os.makedirs("models", exist_ok=True)
        response = requests.get(MODEL_URL)
        with open(MODEL_PATH, "wb") as f:
            f.write(response.content)
        print("Model downloaded successfully!")

# Call before using the model
download_model() 
