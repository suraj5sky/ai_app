import os
import requests
import uuid
from dotenv import load_dotenv

load_dotenv()

huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

HF_API_URL = "https://api-inference.huggingface.co/models/prompthero/openjourney"
OAI_IMAGE_API_URL = "https://api.openai.com/v1/images/generations"

HEADERS_HF = {
    "Authorization": f"Bearer {huggingface_api_key}"
}

HEADERS_OAI = {
    "Authorization": f"Bearer {openai_api_key}",
    "Content-Type": "application/json"
}

def generate_image(prompt, resolution="1024x1024"):
    width, height = map(int, resolution.split("x"))  # Convert "1024x1024" → 1024, 1024

    image = model.generate(prompt, width=width, height=height, quality="high")  
    image.save(f"static/output/generated_image_{resolution}.png")

    return f"static/output/generated_image_{resolution}.png"

def generate_image(prompt, output_folder="static/output", use_openai=False):
    try:
        os.makedirs(output_folder, exist_ok=True)
        image_name = f"{uuid.uuid4().hex}.png"
        image_path = os.path.join(output_folder, image_name)

        if use_openai:
            print("🧠 Using OpenAI for image generation...")
            payload = {
                "prompt": prompt,
                "n": 1,
                "size": "512x512"
            }
            response = requests.post(OAI_IMAGE_API_URL, headers=HEADERS_OAI, json=payload)
            response.raise_for_status()
            data = response.json()
            image_url = data["data"][0]["url"]

            img_data = requests.get(image_url).content
            with open(image_path, 'wb') as f:
                f.write(img_data)

            return {
                "status": "success",
                "image_path": image_path,
                "url": f"/static/output/{image_name}"
            }

        else:
            print("🎨 Using Hugging Face for image generation...")
            payload = {"inputs": prompt}
            response = requests.post(HF_API_URL, headers=HEADERS_HF, json=payload)
            if response.status_code == 503:
                return {
                    "status": "error",
                    "message": "Hugging Face model is temporarily unavailable (503). Please try again after some time."
                }
            response.raise_for_status()

            if response.headers.get("content-type", "").startswith("image"):
                with open(image_path, "wb") as f:
                    f.write(response.content)
                return {
                    "status": "success",
                    "image_path": image_path,
                    "url": f"/static/output/{image_name}"
                }
            else:
                return {
                    "status": "error",
                    "message": "Hugging Face returned non-image response."
                }

    except Exception as e:
        return {"status": "error", "message": str(e)}
