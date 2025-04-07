from flask import Flask, request, jsonify, send_from_directory, url_for, render_template
from flask_cors import CORS
from modules.image_gen import generate_image
from modules.video_creator import create_video
from modules.lipsync import run_lipsync
from dotenv import load_dotenv
from datetime import datetime
from gtts import gTTS
from TTS.api import TTS
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
from moviepy.editor import VideoFileClip

# Load environment variables
load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
COQUI_MODEL_DIR = os.getenv("COQUI_MODEL_DIR", "coqui_models")

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

# Complete Voice Configuration
LANGUAGES = ["hindi", "english", "spanish", "french", "arabic", "german", "japanese", 
             "bengali", "gujarati", "tamil", "punjabi", "kannada"]

VOICES = {
    "hindi": [
	     {
            "id": "hi-IN-MadhurNeural",
            "name": "Surja (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits",
            "style": "authoritative",
            "use_cases": ["news", "presentations"],
            "description": "Deep commanding voice for professional narration",
            "sample_text": "Hello Dosto, मैं सूरज। आज का मुख्य समाचार सुनिए...",
            "age_range": "30-45",
            "mood": "professional"
        },
        {
            "id": "hi-IN-SwaraNeural",
            "name": "Riya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits--female",
            "style": "cheerful",
            "use_cases": ["storytelling", "customer_service"],
            "description": "Warm and friendly voice ideal for conversational apps",
            "sample_text": "आपका स्वागत है! मैं रिया आपके लिए कहानी सुनाउंगी...",
            "age_range": "20-35",
            "mood": "friendly"
        },
        {
            "id": "hi-IN-KedarNeural",
            "name": "Roohi (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits",
            "style": "serious",
            "use_cases": ["documentaries", "education"],
            "description": "Clear and precise voice for instructional content",
            "sample_text": "आज हम विज्ञान के एक महत्वपूर्ण सिद्धांत पर चर्चा करेंगे...",
            "age_range": "35-50",
            "mood": "professional"
        },
        {
            "id": "hi-IN-MadhurNeural",
            "name": "Aarav (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits",
            "style": "authoritative",
            "use_cases": ["news", "presentations"],
            "description": "Deep commanding voice for professional narration",
            "sample_text": "नमस्ते, मैं आरव हूँ। आज का समाचार सुनिए...",
            "age_range": "30-40",
            "mood": "professional"
        },
        {
            "id": "en-US-AndrewMultilingualNeural",
            "name": "Ravi (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "natural",
            "use_cases": ["storytelling", "educational", "motivational"],
            "description": "Warm and clear Hindi voice, ideal for narration and YouTube content",
            "sample_text": "एक समय की बात है, एक छोटे से गाँव में एक बच्चा रहता था...",
            "age_range": "30-40",
            "mood": "inspiring"
        },
         {
            "id": "en-US-BrianMultilingualNeural",
            "name": "Anup (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "deep",
            "use_cases": ["mythological", "devotional", "voiceovers"],
            "description": "Deep and authoritative Hindi voice perfect for spiritual or historical content",
            "sample_text": "भगवान श्रीराम ने अपने अनुयायियों को धर्म का मार्ग दिखाया...",
            "age_range": "35-50",
            "mood": "calm & powerful"
        },
        {
            "id": "en-US-BrianNeural",
            "name": "Brian (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! मैं आज आपकी सहायता कैसे करूं?",
            "age_range": "25-35",
            "mood": "Copilot  Warm"
        },
        {
            "id": "hi-IN-SwaraNeural",
            "name": "Anchal (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits--female",
            "style": "cheerful",
            "use_cases": ["storytelling", "customer_service"],
            "description": "Warm and friendly voice ideal for children's content",
            "sample_text": "आज मैं आपके लिए एक कहानी लायी हूँ...",
            "age_range": "20-30",
            "mood": "friendly"
        },
        {
            "id": "hi-IN-PoojaNeural",
            "name": "Kavya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits--female",
            "style": "calm",
            "use_cases": ["meditation", "audiobooks"],
            "description": "Soothing voice perfect for relaxation content",
            "sample_text": "आँखें बंद करें और गहरी सांस लें...",
            "age_range": "25-40",
            "mood": "relaxing"
        }
    ],
    "english": [
        {
            "id": "en-US-DavisNeural",
            "name": "Sophia (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-ljspeech-tacotron2-DDC",
            "style": "professional",
            "use_cases": ["business", "presentations"],
            "description": "Clear and articulate voice for professional content",
            "sample_text": "Hello everyone. Let's begin today's presentation.",
            "age_range": "30-45",
            "mood": "authoritative"
        },
        {
            "id": "en-IN-PrabhatNeural",
            "name": "Prabhat (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "education"],
            "description": "Approachable voice for interactive applications",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "warm"
        },
        {
            "id": "en-IN-NeerjaNeural",
            "name": "Sapna (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "education"],
            "description": "Approachable voice for interactive applications",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "warm"
        },
        {
            "id": "en-IN-NeerjaExpressiveNeural",
            "name": "Neerja (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "education"],
            "description": "Approachable voice for interactive applications",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "warm"
        },
        {
            "id": "en-US-AndrewNeural",
            "name": "Shiva (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "Copilot  Warm"
        },
        {
            "id": "en-US-ChristopherNeural",
            "name": "Devas (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "News, Novel"
        },
         {
            "id": "en-US-EricNeural",
            "name": "Deva (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "News, Novel"
        },
         {
            "id": "en-US-RogerNeural",
            "name": "Anand (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "News, Novel"
        },
        {
            "id": "en-US-RogerNeural",
            "name": "Shobhit (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "Conversation",
            "use_cases": ["customer_service", "education"],
            "description": "Conversation, Copilot  Warm, Confident, Authentic, Honest",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "News, Novel"
        },
        {
            "id": "en-US-JennyNeural",
            "name": "Supriya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "education"],
            "description": "Approachable voice for interactive applications",
            "sample_text": "Hello! How can I help you today?",
            "age_range": "25-35",
            "mood": "warm"
        },    
        {
            "id": "en-IN-PriyaNeural",
            "name": "Priya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "conversational",
            "use_cases": ["educational", "narration", "explainer"],
            "description": "Friendly and clear voice ideal for educational content",
            "sample_text": "Let’s explore the basics of machine learning today...",
            "age_range": "25-35",
            "mood": "warm"
        },
        {
            "id": "en-US-GuyNeural",
            "name": "Abhi (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "en-ljspeech-glow-tts",
            "style": "casual",
            "use_cases": ["podcasts", "entertainment"],
            "description": "Natural conversational voice for casual content",
            "sample_text": "Hey there! Welcome to the show.",
            "age_range": "20-40",
            "mood": "engaging"
        },
        {
            "id": "en-US-AriaNeural",
            "name": "Sanaya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "expressive",
            "use_cases": ["storytelling", "animation"],
            "description": "Dynamic voice with emotional range",
            "sample_text": "Once upon a time in a magical kingdom...",
            "age_range": "20-30",
            "mood": "playful"
        },
        {
            "id": "en-AU-ElsieNeural",
            "name": "Nancy (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "expressive",
            "use_cases": ["storytelling", "animation"],
            "description": "Dynamic voice with emotional range",
            "sample_text": "Once upon a time in a magical kingdom...",
            "age_range": "20-30",
            "mood": "playful"
        },
        {
            "id": "en-CA-ClaraNeural",
            "name": "Neha (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "bold",
            "use_cases": ["trailers", "promos", "tech"],
            "description": "Bold, cinematic voice perfect for trailers",
            "sample_text": "This summer, prepare for an unforgettable journey...",
            "age_range": "20-30",
            "mood": "dramatic"
        },
        {
            "id": "en-AU-NatashaNeural",
            "name": "Zara (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "empathetic",
            "use_cases": ["healthcare", "emotional storytelling"],
            "description": "Soothing voice with an empathetic tone",
            "sample_text": "We’re here to support you on your wellness journey...",
            "age_range": "30-45",
           "mood": "calm"
        },
        {
            "id": "en-US-NancyNeural",
            "name": "Tanya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "en-vctk-vits",
            "style": "elegant",
            "use_cases": ["documentaries", "luxury_brands"],
            "description": "Sophisticated voice for premium content",
            "sample_text": "The finest craftsmanship begins with passion...",
            "age_range": "30-50",
            "mood": "refined"
        }
    ],
    "spanish": [
        {
            "id": "es-ES-AlvaroNeural",
            "name": "Carlos (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "es-css10-vits",
            "style": "formal",
            "use_cases": ["business", "education"],
            "description": "Professional Spanish voice for formal contexts",
            "sample_text": "Buenos días. Comencemos nuestra reunión.",
            "age_range": "35-50",
            "mood": "professional"
        },
        {
            "id": "es-ES-ElviraNeural",
            "name": "Sofia (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "es-css10-vits",
            "style": "warm",
            "use_cases": ["customer_service", "audiobooks"],
            "description": "Friendly Spanish voice for everyday interactions",
            "sample_text": "Hola, ¿en qué puedo ayudarte hoy?",
            "age_range": "25-40",
            "mood": "friendly"
        }
    ],
    "french": [
        {
            "id": "fr-FR-HenriNeural",
            "name": "Luc (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "fr-css10-vits",
            "style": "sophisticated",
            "use_cases": ["luxury_brands", "education"],
            "description": "Elegant French voice with Parisian accent",
            "sample_text": "Bonjour, je m'appelle Luc. Enchanté.",
            "age_range": "30-50",
            "mood": "refined"
        },
        {
            "id": "fr-FR-DeniseNeural",
            "name": "Élodie (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "fr-css10-vits",
            "style": "charming",
            "use_cases": ["fashion", "travel"],
            "description": "Charming voice with melodic French intonation",
            "sample_text": "Bienvenue à Paris, la ville de l'amour!",
            "age_range": "25-40",
            "mood": "playful"
        }
    ],
    "arabic": [
        {
            "id": "ar-SA-HamedNeural",
            "name": "Khalid (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "ar-css10-vits",
            "style": "authoritative",
            "use_cases": ["news", "religious"],
            "description": "Strong traditional Arabic voice",
            "sample_text": "السلام عليكم. أهلاً وسهلاً بكم.",
            "age_range": "35-55",
            "mood": "formal"
        },
        {
            "id": "ar-SA-ZariyahNeural",
            "name": "Layla (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "ar-css10-vits",
            "style": "gentle",
            "use_cases": ["education", "children"],
            "description": "Soft-spoken Arabic voice for nurturing content",
            "sample_text": "مرحباً صغيري، هل تريد أن أقرأ لك قصة؟",
            "age_range": "25-40",
            "mood": "caring"
        }
    ],
    "german": [
        {
            "id": "de-DE-ConradNeural",
            "name": "Max (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "de-css10-vits",
            "style": "precise",
            "use_cases": ["technology", "education"],
            "description": "Clear and precise German voice",
            "sample_text": "Guten Tag. Willkommen zu unserer Vorstellung.",
            "age_range": "30-50",
            "mood": "professional"
        },
        {
            "id": "de-DE-KatjaNeural",
            "name": "Anna (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "de-css10-vits",
            "style": "friendly",
            "use_cases": ["customer_service", "tourism"],
            "description": "Approachable German voice for everyday use",
            "sample_text": "Hallo! Wie kann ich Ihnen helfen?",
            "age_range": "25-40",
            "mood": "welcoming"
        }
    ],
    "japanese": [
        {
            "id": "ja-JP-KeitaNeural",
            "name": "Haruto (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "ja-css10-vits",
            "style": "formal",
            "use_cases": ["business", "education"],
            "description": "Polite Japanese voice for professional settings",
            "sample_text": "こんにちは、私はハルトと申します。よろしくお願いします。",
            "age_range": "30-50",
            "mood": "respectful"
        },
        {
            "id": "ja-JP-NanamiNeural",
            "name": "Sakura (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "ja-css10-vits",
            "style": "gentle",
            "use_cases": ["entertainment", "children"],
            "description": "Soft Japanese voice with friendly tone",
            "sample_text": "おはようございます！今日も元気にいきましょう！",
            "age_range": "20-35",
            "mood": "cheerful"
        },
        {
            "id": "hi-IN-MadhurNeural",
            "name": "Aarav (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits",
            "style": "authoritative",
            "use_cases": ["news", "presentations"],
            "description": "Deep commanding voice for professional narration",
            "sample_text": "नमस्ते, मैं आरव हूँ। आज का समाचार सुनिए...",
            "age_range": "30-40",
            "mood": "professional"
        },
        {
            "id": "hi-IN-SwaraNeural",
            "name": "Ananya (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "hi-cv-vits--female",
            "style": "cheerful",
            "use_cases": ["storytelling", "customer_service"],
            "description": "Warm and friendly voice ideal for children's content",
            "sample_text": "आज मैं आपके लिए एक कहानी लायी हूँ...",
            "age_range": "20-30",
            "mood": "friendly"
        }
    ],
    "bengali": [
        {
            "id": "bn-IN-TanishaaNeural",
            "name": "Tanishaa (Female)",
            "gender": "female",
            "service": "edge",
            "coqui_fallback": "bn-cv-vits",
            "style": "gentle",
            "use_cases": ["audiobooks", "ASMR"],
            "description": "Soft-spoken voice with lyrical quality",
            "sample_text": "আজ আমরা একটি নতুন গল্প শুরু করব...",
            "age_range": "25-35",
            "mood": "calm"
        },
        {
            "id": "bn-IN-BashkarNeural",
            "name": "Bashkar (Male)",
            "gender": "male",
            "service": "edge",
            "coqui_fallback": "bn-cv-vits",
            "style": "serious",
            "use_cases": ["documentaries", "news"],
            "description": "Authoritative delivery for factual content",
            "sample_text": "এই সংবাদটি গুরুত্বপূর্ণ...",
            "age_range": "35-45",
            "mood": "professional"
        }
    ],
    "punjabi": [
        {
            "id": None,
            "name": "Shruti (Female)",
            "gender": "female",
            "service": "coqui",
            "coqui_model": "pa-custom-v1",
            "style": "energetic",
            "use_cases": ["marketing", "podcasts"],
            "description": "High-energy voice for advertisements",
            "sample_text": "ਹੈਲੋ, ਮੈਂ ਓਜਸ ਹਾਂ...",
            "age_range": "25-40",
            "mood": "enthusiastic",
            "training_required": True,
            "training_steps": [
                "1. Collect 1 hour Punjabi male recordings",
                "2. Fine-tune on coqui.ai",
                "3. Host model on Render"
            ]
        },
        {
            "id": None,
            "name": "Vaani (Female)",
            "gender": "female",
            "service": "coqui",
            "coqui_model": "pa-cv-vits--female",
            "style": "warm",
            "use_cases": ["storytelling", "education"],
            "description": "Motherly tone for folk tales",
            "sample_text": "ਇੱਕ ਵਾਰ ਦੀ ਗੱਲ ਹੈ...",
            "age_range": "30-50",
            "mood": "nurturing"
        }
    ]
}

# Coqui TTS Fallback Strategy
COQUI_VOICES = {
    "punjabi": {
        "male": {
            "id": "pa-IN-vits",
            "name": "Ojas",
            "steps": [
                "1. Collect 1 hour Punjabi male recordings",
                "2. Fine-tune on coqui.ai",
                "3. Host model on Render"
            ]
        }
    },
    "kannada": {
        "female": {
            "id": "kn-IN-vits",
            "name": "Sapna",
            "pretrained": True
        }
    }
}

GTTS_LANG_CODES = {
    "hindi": "hi",
    "english": "en",
    "spanish": "es",
    "french": "fr",
    "arabic": "ar",
    "german": "de",
    "japanese": "ja",
    "bengali": "bn",
    "gujarati": "gu",
    "tamil": "ta",
    "punjabi": "pa",
    "kannada": "kn"
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
VOICE_PREVIEWS = 'static/voice_previews'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# Create directories
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER, 'models', 
               AUDIO_FOLDER, 'static/images', COQUI_MODEL_DIR, VOICE_PREVIEWS]:
    os.makedirs(folder, exist_ok=True)

def download_wav2lip_model():
    if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 100_000_000:
        logger.info("Wav2Lip model already exists")
        return MODEL_PATH

    file_id = "1Z6BUbVI0LqIzRrepoo13pflWE_XUXETs"
    model_url = f"https://drive.google.com/uc?id={file_id}"
    
    logger.info("Downloading Wav2Lip model...")
    try:
        gdown.download(model_url, MODEL_PATH, quiet=False)
        if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) < 100_000_000:
            raise ValueError("Downloaded file is incomplete or corrupted")
        logger.info("Wav2Lip model downloaded successfully")
        return MODEL_PATH
    except Exception as e:
        logger.error(f"Failed to download model: {str(e)}")
        if os.path.exists(MODEL_PATH):
            os.remove(MODEL_PATH)
        raise

def save_audio_file(audio_data, voice_id, extension="wav"):
    try:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"tts_{voice_id}_{timestamp}.{extension}"
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
    try:
        communicate = edge_tts.Communicate(text, voice_id)
        temp_file = os.path.join(TEMP_FOLDER, f"edge_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3")
        await communicate.save(temp_file)
        return temp_file
    except Exception as e:
        logger.error(f"Edge-TTS generation error: {str(e)}")
        return None

def generate_with_edge(text, voice_id):
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

def generate_with_coqui(text, model_name):
    try:
        tts = TTS(model_name=f"tts_models/{model_name}")
        temp_file = os.path.join(TEMP_FOLDER, f"coqui_{datetime.now().strftime('%Y%m%d%H%M%S')}.wav")
        tts.tts_to_file(text=text, file_path=temp_file)
        
        with open(temp_file, 'rb') as f:
            audio_data = f.read()
        os.remove(temp_file)
        return audio_data
    except Exception as e:
        logger.error(f"Coqui TTS error: {str(e)}")
        return None

def generate_with_gtts(text, lang='en'):
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
    try:
        return jsonify({
            'status': 'success',
            'languages': LANGUAGES,
            'voices': VOICES,
            'coqui_models': COQUI_VOICES,
            'max_char_limit': 5000
        })
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/voice-details', methods=['GET'])
def get_voice_details():
    try:
        return jsonify({
            'status': 'success',
            'voice_metadata': {
                'styles': ["authoritative", "cheerful", "calm", "energetic", "serious", "gentle"],
                'use_cases': ["storytelling", "education", "marketing", "news", "customer_service", "audiobooks"],
                'age_ranges': ["20-30", "30-40", "40-50"],
                'moods': ["professional", "friendly", "calm", "enthusiastic"]
            }
        })
    except Exception as e:
        logger.error(f"Error getting voice details: {str(e)}")
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
            'message': 'Text exceeds 5000 character limit',
            'max_limit': 5000
        }), 400

    try:
        selected_voice = next((v for v in VOICES.get(language, []) if v.get('id') == voice_id or v.get('coqui_model') == voice_id), None)
        
        if not selected_voice:
            return jsonify({'status': 'error', 'message': 'Invalid voice selection'}), 400

        # Determine service to use
        service = selected_voice.get('service', 'edge')
        audio_data = None
        
        if service == 'edge' and selected_voice.get('id'):
            audio_data = generate_with_edge(text, selected_voice['id'])
        elif service == 'coqui' and selected_voice.get('coqui_model'):
            audio_data = generate_with_coqui(text, selected_voice['coqui_model'])
        
        # Fallback system
        if not audio_data:
            if service == 'edge' and 'coqui_fallback' in selected_voice:
                logger.info(f"Falling back to Coqui: {selected_voice['coqui_fallback']}")
                audio_data = generate_with_coqui(text, selected_voice['coqui_fallback'])
                if audio_data:
                    selected_voice['name'] += " (Coqui Fallback)"
            
            if not audio_data:
                logger.info("Falling back to gTTS")
                lang_code = GTTS_LANG_CODES.get(language, "en")
                audio_data = generate_with_gtts(text, lang=lang_code)
                if audio_data:
                    selected_voice['name'] += " (gTTS Fallback)"

        if not audio_data:
            raise Exception("All TTS methods failed")

        extension = "mp3" if selected_voice.get('service') == 'gtts' else "wav"
        save_result = save_audio_file(audio_data, voice_id, extension)
        if save_result['status'] != 'success':
            raise Exception(save_result['message'])

        response = {
            'status': 'success',
            'audio_url': save_result['audio_url'],
            'voice_used': selected_voice['name'],
            'language': language,
            'service': service,
            'voice_metadata': {
                'style': selected_voice.get('style'),
                'use_cases': selected_voice.get('use_cases', []),
                'description': selected_voice.get('description'),
                'sample_text': selected_voice.get('sample_text'),
                'age_range': selected_voice.get('age_range'),
                'mood': selected_voice.get('mood')
            }
        }
        return jsonify(response)

    except Exception as e:
        logger.error(f"TTS generation error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/voice-preview/<voice_id>')
def voice_preview(voice_id):
    try:
        # Find voice in configuration
        voice = None
        for lang in VOICES.values():
            for v in lang:
                if v.get('id') == voice_id or v.get('coqui_model') == voice_id:
                    voice = v
                    break
            if voice:
                break

        if not voice:
            return jsonify({'status': 'error', 'message': 'Voice not found'}), 404

        # Check if preview exists
        preview_file = f"{voice_id}_preview.wav"
        preview_path = os.path.join(VOICE_PREVIEWS, preview_file)
        
        if not os.path.exists(preview_path):
            # Generate preview if missing
            sample_text = voice.get('sample_text', 'Hello, this is a sample')
            if voice.get('service') == 'edge' and voice.get('id'):
                audio_data = generate_with_edge(sample_text, voice['id'])
            elif voice.get('service') == 'coqui' and voice.get('coqui_model'):
                audio_data = generate_with_coqui(sample_text, voice['coqui_model'])
            else:
                lang_code = GTTS_LANG_CODES.get(voice.get('language'), "en")
                audio_data = generate_with_gtts(sample_text, lang=lang_code)
            
            if not audio_data:
                raise Exception("Preview generation failed")
            
            with open(preview_path, 'wb') as f:
                f.write(audio_data)

        return send_from_directory(VOICE_PREVIEWS, preview_file, mimetype="audio/wav")

    except Exception as e:
        logger.error(f"Voice preview error: {str(e)}")
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