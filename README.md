# 🎬 AI Tools Creator

Welcome to **AI Tools Creator** – an intelligent and extensible Flask-based backend designed to bring your AI content creation workflows to life. This project combines the power of **Text-to-Speech**, **AI-generated images**, and **automated video creation**, all from simple API calls.

Whether you're building avatar videos, YouTube reels, storytelling apps, or AI-powered content platforms – this toolkit gets you started fast and easy.

---

## ✨ Key Features

- 🎧 **Text-to-Speech (TTS)** with `gTTS`
- 🖼️ **AI Image Generation** using Hugging Face (default) or OpenAI DALL·E (optional)
- 🎞️ **Video Creation**: Combine generated audio and image into an auto-generated video
- 🔄 **CORS Enabled**: Smooth cross-origin communication for frontend integration
- 📡 **Simple API Design**: Fast to integrate and easy to extend
- 🧱 **Modular Codebase**: Add avatars, subtitles, or custom models easily

---

## 🧩 Project Structure

ai_app/ ├── app.py # Main Flask application ├── modules/ │ ├── init.py │ ├── tts.py # Text-to-Speech logic │ ├── image_gen.py # Image generation logic │ └── video_creator.py # Combines audio + image to create video ├── static/ │ ├── uploads/ # Uploaded user files (if any) │ └── output/ # Generated audio, images, and videos ├── .env # API keys and secrets ├── requirements.txt # Python dependencies └── README.md # Project documentation

yaml
Copy
Edit

---

## 🚀 Getting Started

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-repo/ai_avatar_video_app.git
cd ai_avatar_video_app
2️⃣ Set Up a Virtual Environment
bash
Copy
Edit
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
3️⃣ Install Dependencies
bash
Copy
Edit
pip install -r requirements.txt
4️⃣ Configure Environment Variables
Create a .env file in the root:

ini
Copy
Edit
HUGGINGFACE_API_KEY=your_huggingface_api_key
OPENAI_API_KEY=your_openai_api_key   # Optional
🧪 Running the Application
bash
Copy
Edit
python app.py
Your Flask API server will be live at:
📍 http://127.0.0.1:5000/

🔌 API Endpoints
✅ Health Check
GET /
Returns a welcome message and API status.

🎧 Generate TTS Audio
POST /api/tts
Payload:

json
Copy
Edit
{
  "text": "Hello world",
  "lang": "en",
  "slow": false
}
Response:

json
Copy
Edit
{
  "status": "success",
  "audio_url": "/static/output/audio_12345.mp3"
}
🖼️ Generate Image
POST /api/generate_image
Payload:

json
Copy
Edit
{
  "prompt": "A robot painting a galaxy",
  "use_openai": false
}
Response:

json
Copy
Edit
{
  "status": "success",
  "image_path": "static/output/image_12345.png",
  "image_url": null
}
🎞️ Generate Video (Optional)
If exposed as an API route or internal utility, this combines the generated image and audio into an .mp4 video. You can add or document the route as needed.

🌐 Deployment Tips
If deploying on a subdomain like:

🔗 https://ai.skyinfinitetech.com

Make sure to:

Configure CORS properly for frontend access

Update your reverse proxy (e.g., Nginx) settings

Keep your .env safe and secure using environment managers

🛠 Tech Stack
Flask – Lightweight web backend

gTTS – Google Text-to-Speech

Hugging Face API – AI image generation

OpenAI SDK (optional) – DALL·E image creation

moviepy, ffmpeg-python – Video generation

Flask-CORS – Cross-origin resource sharing

See requirements.txt for the full list of libraries.

👨‍💻 Author & Credits
Developed by Suraj Yadav(SKY Infinite 🚀)

🌐 www.skyinfinitetech.com

📺 YouTube: SKY Infinite Learning

💡 Your creativity is the only limit. Build amazing AI-powered content with ease.
