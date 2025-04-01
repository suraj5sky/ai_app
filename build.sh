#!/bin/bash
# build.sh

# Install system dependencies
apt-get update && apt-get install -y espeak ffmpeg

# Create models directory if it doesn't exist
mkdir -p models

# Download Wav2Lip model (if not already present)
if [ ! -f "models/wav2lip.pth" ]; then
    wget https://drive.google.com/uc?id=1DnMDc4SsVtOxMuSU62jRkDIS1CqRZ3AS -O models/wav2lip.pth
fi

# Install Python dependencies
pip install -r requirements.txt