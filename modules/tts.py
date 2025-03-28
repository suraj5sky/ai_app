from gtts import gTTS
import os
import uuid

def generate_tts(text, output_folder, lang='en', slow=False):
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Generate unique filename
    filename = f"{uuid.uuid4()}.mp3"
    path = os.path.join(output_folder, filename)

    # Generate speech
    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(path)

    return path.replace(os.sep, '/')
