🎬 AI Tools Creator::

Welcome to the AI Tools Creator, a powerful Flask-based backend application that lets you generate:

🎧 Text-to-Speech (TTS) audio using gTTS

🖼️ AI-generated images using Hugging Face or OpenAI

🎞️ Auto-generated videos from audio + image

Perfect for building AI-powered avatar videos, reels, YouTube content, storytelling apps, and more.

📁 Project Structure::

ai_app/
├── app.py                  # Main Flask application
├── modules/                # Core functionality modules
│   ├── __init__.py
│   ├── tts.py              # Text-to-Speech (gTTS)
│   ├── image_gen.py        # Image generation via Hugging Face / OpenAI
│   └── video_creator.py    # Merges image & audio into a video
├── static/
│   ├── uploads/            # User-uploaded files (if any)
│   └── output/             # Generated audio, images, videos
├── .env                    # API keys for Hugging Face / OpenAI
├── requirements.txt        # All required dependencies
└── README.md               # Project documentation

🚀 Features::
✅ Text to Speech using gTTS

✅ Image Generation via Hugging Face API (default) or OpenAI DALL·E (optional)

✅ Video Creation combining generated image + audio

✅ Cross-Origin Resource Sharing (CORS) enabled

✅ Health Check and static file support

✅ Easy to extend for avatars, subtitles, custom voices

🔧 Installation::
Clone the project:

git clone https://github.com/your-repo/ai_avatar_video_app.git
cd ai_avatar_video_app
Create & activate virtual environment:


python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
Install dependencies:


pip install -r requirements.txt
Set up environment variables:

Create a .env file at the root:


HUGGINGFACE_API_KEY=your_huggingface_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional
🧪 Running the App

python app.py
Server will run on: http://127.0.0.1:5000/

🔌 API Endpoints
✅ Root

GET /
Returns welcome message and status.

🎧 Generate TTS Audio::

POST /api/tts
Payload:

{
  "text": "Hello World",
  "lang": "en",
  "slow": false
}
Response:


{
  "status": "success",
  "audio_url": "/static/output/audio_12345.mp3"
}

🖼️ Generate Image::

POST /api/generate_image
Payload:


{
  "prompt": "A futuristic city at night",
  "use_openai": false
}

Response:


{
  "status": "success",
  "image_path": "static/output/image_12345.png",
  "image_url": null  // Only if OpenAI used
}
🎞️ (Optional) Generate Video
If exposed via a separate route or internal use, document it accordingly.

📦 Deployment Notes
If deploying to a subdomain like:


ai.skyinfinitetech.com
Update your nginx/apache config and enable CORS for the front-end at:


ai.skyinfinitetech.com

🛠 Dependencies::
Check requirements.txt for all packages.

Includes:

Flask

Flask-CORS

gTTS

ffmpeg-python

OpenAI SDK

moviepy

imageio

numpy, scipy, librosa

scikit-learn

matplotlib (for future visualization or debugging)

🙌 Author & Credits::

Developed by SKY Infinite:->

Visit: www.skyinfinitetech.com
YouTube Channel: SKY Infinite Learning


Happy Happy, Thanks!!
=============================================
