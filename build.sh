#!/bin/bash
set -e  # Exit on error

# Install gdown via pip (not apt)
pip install gdown

# Create models directory
mkdir -p models

# Download Wav2Lip model
gdown "https://drive.google.com/uc?id=1Z6BUbVI0LqIzRrepoo13pflWE_XUXETs" -O models/wav2lip.pth

# Install Python dependencies
pip install -r requirements.txt