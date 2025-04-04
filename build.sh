#!/bin/bash
set -e

# Create models directory
mkdir -p models

# Try multiple download methods
{
    # Method 1: gdown
    gdown "https://drive.google.com/uc?id=1Z6BUbVI0LqIzRrepoo13pflWE_XUXETs" -O models/wav2lip.pth ||
    # Method 2: curl fallback
    curl -L "https://drive.google.com/uc?export=download&id=1Z6BUbVI0LqIzRrepoo13pflWE_XUXETs" --output models/wav2lip.pth ||
    # Method 3: wget fallback
    wget --no-check-certificate "https://docs.google.com/uc?export=download&id=1Z6BUbVI0LqIzRrepoo13pflWE_XUXETs" -O models/wav2lip.pth
}

# Verify download
if [ ! -f models/wav2lip.pth ]; then
    echo "❌ All download methods failed!"
    exit 1
fi

pip install -r requirements.txt