#!/bin/bash
# build.sh

# Install system dependencies
apt-get update && apt-get install -y espeak ffmpeg

# Create models directory inside the correct project directory if it doesn't exist
mkdir -p /opt/render/project/src/models  # This ensures it is inside the Render project directory

# Download Wav2Lip model (if not already present)
if [ ! -f "/opt/render/project/src/models/wav2lip.pth" ]; then
    echo "Downloading Wav2Lip model..."
    pip install gdown  # Ensure gdown is installed
    gdown --id 1DnMDc4SsVtOxMuSU62jRkDIS1CqRZ3AS -O /opt/render/project/src/models/wav2lip.pth
    echo "Download complete!"
else
    echo "Wav2Lip model already exists."
fi

# Install Python dependencies
pip install -r requirements.txt