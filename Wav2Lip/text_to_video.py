from moviepy.editor import *
from gtts import gTTS
import pyttsx3
import numpy as np
import os
import requests
import subprocess
import time
import textwrap
import json
from moviepy.config import change_settings
import random
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import imageio_ffmpeg as ffmpeg

# ✅ Set FFmpeg Path
os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg.get_ffmpeg_version()

# ✅ Set ImageMagick Path (Fix for Windows)
change_settings({"IMAGEMAGICK_BINARY": r"C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"})

# ✅ AI Voice Selection (Google TTS, ElevenLabs, pyttsx3)
elevenlabs_api_key = "YOUR_ELEVENLABS_API_KEY"
elevenlabs_voice_id = "YOUR_VOICE_ID"

languages = {
    "en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French",
    "de": "German", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "ru": "Russian", "ar": "Arabic", "pt": "Portuguese", "it": "Italian"
}

def get_ai_voice(text, voice_id="en-US", engine="google"):
    if engine == "elevenlabs" and elevenlabs_api_key:
        return generate_elevenlabs_voice(text, voice_id)
    elif engine == "pyttsx3":
        return generate_pyttsx3_voice(text)
    else:
        return generate_google_tts(text, voice_id)

def generate_google_tts(text, lang="en"):
    tts = gTTS(text, lang=lang)
    tts.save("audio.mp3")
    return "audio.mp3"

def generate_elevenlabs_voice(text, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": elevenlabs_api_key,
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
    })
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        with open("audio.mp3", "wb") as f:
            f.write(response.content)
        return "audio.mp3"
    except requests.exceptions.RequestException as e:
        print(f"❌ Error generating voice: {e}")
        return None

def generate_pyttsx3_voice(text):
    engine = pyttsx3.init()
    engine.save_to_file(text, "audio.mp3")
    engine.runAndWait()
    return "audio.mp3"

# ✅ Background Music Selection
def download_background_music():
    music_file = "background_music.mp3"
    if os.path.exists(music_file):
        return music_file
    music_urls = [
        "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/no_curator/Kevin_MacLeod/Bossa_Antigua.mp3",
        "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    ]
    music_url = random.choice(music_urls)
    try:
        response = requests.get(music_url, stream=True, timeout=10)
        response.raise_for_status()
        with open(music_file, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        return music_file
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading music: {e}")
        return None

# ✅ Lip Sync with Wav2Lip
def lip_sync_with_wav2lip(face_video, audio_file, output_video):
    try:
        command = f"python Wav2Lip/inference.py --checkpoint_path Wav2Lip/checkpoints/wav2lip.pth --face {face_video} --audio {audio_file} --outfile {output_video}"
        subprocess.run(command, shell=True, check=True)
        return output_video
    except subprocess.CalledProcessError as e:
        print(f"❌ Wav2Lip Error: {e}")
        return None

# ✅ Generate Video
def generate_video(text, voice_id, engine="google", face_video="face.mp4"):
    audio_file = get_ai_voice(text, voice_id, engine)
    if not audio_file:
        print("❌ Skipping video due to audio generation failure.")
        return
    lip_synced_video = lip_sync_with_wav2lip(face_video, audio_file, "lip_synced.mp4")
    if not lip_synced_video:
        return
    video = VideoFileClip(lip_synced_video)
    txt_clip = TextClip(text, fontsize=50, color='white', font="Arial-Bold", size=(1280, 100)).set_duration(video.duration).set_position("center").fadein(1).fadeout(1)
    music_file = download_background_music()
    if music_file:
        bg_music = AudioFileClip(music_file).set_duration(video.duration).volumex(0.3)
        final_audio = CompositeAudioClip([video.audio, bg_music])
    else:
        final_audio = video.audio
    final_video = CompositeVideoClip([video, txt_clip]).set_audio(final_audio)
    filename = "output_" + str(int(time.time())) + ".mp4"
    final_video.write_videofile(filename, fps=30, codec="libx264")
    print(f"✅ Video Created: {filename}")

# ✅ Bulk Video Processing
def process_videos():
    text_list = [
        {"text": "Welcome to AI Video Generation.", "voice": "en-US", "engine": "elevenlabs"},
        {"text": "Learn how AI creates videos automatically!", "voice": "en-GB", "engine": "google"},
        {"text": "Offline speech synthesis example.", "voice": "en", "engine": "pyttsx3"}
    ]
    with ThreadPoolExecutor(max_workers=min(len(text_list), os.cpu_count())) as executor:
        executor.map(lambda item: generate_video(item["text"], item["voice"], item["engine"]), text_list)

# ✅ Start Video Generation
if __name__ == "__main__":
    process_videos()
