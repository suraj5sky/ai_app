# modules/lipsync.py

import os
import subprocess
from pathlib import Path

def run_lipsync(face_image_path, audio_path, output_path,
                wav2lip_model_path="ai_app/modules/wav2lip.pth"):
    """
    Runs the Wav2Lip inference to generate a lip-synced video.

    Args:
        face_image_path (str): Path to the face image.
        audio_path (str): Path to input audio file.
        output_path (str): Path where the output video will be saved.
        wav2lip_model_path (str): Path to the Wav2Lip model (.pth).

    Returns:
        bool: True if successful, False if failed
    """
    try:
        # Build absolute paths
        base_dir = Path(__file__).resolve().parent.parent
        inference_script = base_dir / "Wav2Lip" / "inference.py"
        model_path = Path(wav2lip_model_path).resolve()

        print("🧠 Wav2Lip Inference Starting...")
        print(f"📸 Face Image: {face_image_path}")
        print(f"🎵 Audio: {audio_path}")
        print(f"💾 Output: {output_path}")
        print(f"📦 Model: {model_path}")
        print(f"📜 Script: {inference_script}")

        # Build the command
        command = [
            "python", str(inference_script),
            "--checkpoint_path", str(model_path),
            "--face", str(face_image_path),
            "--audio", str(audio_path),
            "--outfile", str(output_path)
        ]

        # Run the subprocess
        subprocess.run(command, check=True)

        print("✅ Lip-sync video created successfully.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error during Wav2Lip execution: {e}")
        return False

    except Exception as ex:
        print(f"❌ Unexpected error in lipsync module: {ex}")
        return False
