#!/bin/bash
set -e  # Exit on errors

set -e  # Exit on errors

# Install system dependencies
apt-get update && apt-get install -y espeak ffmpeg



# Download model
mkdir -p models
gdown "https://drive.google.com/drive/u/1/folders/1Z6BUbVI0LqIzRrepoo13pflWE_XUXETs" -O models/wav2lip.pth

# Install dependencies
pip install -r requirements.txt


