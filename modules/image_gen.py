import os
import requests
import uuid
import time
from dotenv import load_dotenv

load_dotenv()

# Configuration
huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Updated to use more reliable Stable Diffusion model
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
OAI_IMAGE_API_URL = "https://api.openai.com/v1/images/generations"

HEADERS_HF = {
    "Authorization": f"Bearer {huggingface_api_key}"
}

HEADERS_OAI = {
    "Authorization": f"Bearer {openai_api_key}",
    "Content-Type": "application/json"
}

def generate_image(
    prompt,
    resolution="1024x1024",
    output_folder="static/output",
    use_openai=False,
    max_retries=3
):
    """Generate image with automatic retry and improved error handling"""
    try:
        os.makedirs(output_folder, exist_ok=True)
        image_name = f"{uuid.uuid4().hex}.png"
        image_path = os.path.join(output_folder, image_name)

        if use_openai:
            # OpenAI implementation
            width, height = map(int, resolution.split('x'))
            size = f"{min(width, 1024)}x{min(height, 1024)}"
            
            payload = {
                "prompt": prompt,
                "n": 1,
                "size": size,
                "response_format": "url"
            }
            
            response = requests.post(
                OAI_IMAGE_API_URL,
                headers=HEADERS_OAI,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            image_url = response.json()["data"][0]["url"]
            img_data = requests.get(image_url, timeout=30).content
            with open(image_path, 'wb') as f:
                f.write(img_data)

        else:
            # Hugging Face implementation with retry logic
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        HF_API_URL,
                        headers=HEADERS_HF,
                        json={"inputs": prompt},
                        timeout=30
                    )

                    if response.status_code == 503:
                        if attempt == max_retries - 1:
                            return {
                                "status": "error",
                                "message": "Model unavailable after multiple retries"
                            }
                        time.sleep(10 * (attempt + 1))  # Exponential backoff
                        continue

                    response.raise_for_status()
                    
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    break

                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        return {
                            "status": "error",
                            "message": f"Request failed: {str(e)}"
                        }
                    time.sleep(5)

        return {
            "status": "success",
            "image_url": f"/static/output/{image_name}",
            "path": image_path
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Generation failed: {str(e)}"
        }