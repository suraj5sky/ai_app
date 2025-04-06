import os
import requests
import uuid
import time
from dotenv import load_dotenv

load_dotenv()

# Configuration
huggingface_api_key = os.getenv("HF_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# API URLs
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
OAI_IMAGE_API_URL = "https://api.openai.com/v1/images/generations"

# Headers
HEADERS_HF = {"Authorization": f"Bearer {huggingface_api_key}"}
HEADERS_OAI = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}

# Supported resolutions
SUPPORTED_RESOLUTIONS = {
    "512x512": (512, 512),
    "1024x1024": (1024, 1024),
    "1080x1920": (1080, 1920),  # Portrait
    "1920x1080": (1920, 1080),  # Landscape
    "default": (1024, 1024)     # Fallback
}

def parse_resolution(resolution_str):
    """Parse resolution string into width and height"""
    if resolution_str in SUPPORTED_RESOLUTIONS:
        return SUPPORTED_RESOLUTIONS[resolution_str]
    
    try:
        if 'x' in resolution_str:
            width, height = map(int, resolution_str.lower().split('x'))
            return (width, height)
    except:
        pass
    
    return SUPPORTED_RESOLUTIONS["default"]

def generate_image(
    prompt,
    resolution="1024x1024",
    use_openai=False,
    output_folder="static/output",
    max_retries=3
):
    """Generate image with resolution support and fallback"""
    try:
        os.makedirs(output_folder, exist_ok=True)
        image_name = f"{uuid.uuid4().hex}.png"
        image_path = os.path.join(output_folder, image_name)

        width, height = parse_resolution(resolution)
        
        if use_openai:
            # OpenAI only supports specific sizes
            oai_sizes = {"256x256", "512x512", "1024x1024"}
            if resolution not in oai_sizes:
                resolution = "1024x1024"  # Fallback for OpenAI
                width, height = 1024, 1024

            payload = {
                "prompt": prompt,
                "n": 1,
                "size": resolution,
                "response_format": "url"
            }

            response = requests.post(
                OAI_IMAGE_API_URL,
                headers=HEADERS_OAI,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                return {"status": "error", "message": f"OpenAI API Error: {response.text}"}

            data = response.json().get("data", [])
            image_url = data[0].get("url") if data else None

            if not image_url:
                return {"status": "error", "message": "Failed to retrieve OpenAI image URL"}

            img_data = requests.get(image_url, timeout=30).content
            with open(image_path, 'wb') as f:
                f.write(img_data)

        else:
            # Hugging Face API Implementation
            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        HF_API_URL,
                        headers=HEADERS_HF,
                        json={"inputs": prompt, "parameters": {"width": width, "height": height}},
                        timeout=30
                    )

                    if response.status_code == 503:
                        if attempt == max_retries - 1:
                            return {"status": "error", "message": "Model unavailable after multiple retries"}
                        time.sleep(10 * (attempt + 1))  # Exponential backoff
                        continue

                    if "image" in response.headers.get("Content-Type", ""):
                        with open(image_path, 'wb') as f:
                            f.write(response.content)
                        break
                    else:
                        return {"status": "error", "message": f"Hugging Face API returned non-image response: {response.text}"}

                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        return {"status": "error", "message": f"Request failed: {str(e)}"}
                    time.sleep(5)

        return {
            "status": "success",
            "image_url": f"/static/output/{image_name}",
            "path": image_path,
            "resolution": f"{width}x{height}"
        }

    except Exception as e:
        return {"status": "error", "message": f"Generation failed: {str(e)}"}