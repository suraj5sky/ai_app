import os
import subprocess
from pathlib import Path
import traceback
import sys


def run_lipsync(face_image_path, audio_path, output_path,
                wav2lip_model_path="modules/wav2lip.pth"):
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
        base_dir = Path(__file__).resolve().parent.parent
        wav2lip_dir = base_dir / "Wav2Lip"
        inference_script = wav2lip_dir / "inference.py"
        model_path = Path(wav2lip_model_path).resolve()

        # Validate paths
        if not inference_script.exists():
            print(f"❌ Wav2Lip inference.py not found at {inference_script}")
            return False
        if not model_path.exists():
            print(f"❌ Wav2Lip model not found at {model_path}")
            return False
        if not Path(face_image_path).exists():
            print(f"❌ Face image not found at {face_image_path}")
            return False
        if not Path(audio_path).exists():
            print(f"❌ Audio file not found at {audio_path}")
            return False

        print("\n🎬 Starting Wav2Lip inference...")
        print(f"📸 Image: {face_image_path}")
        print(f"🎵 Audio: {audio_path}")
        print(f"📦 Model: {model_path}")
        print(f"📜 Script: {inference_script}")
        print(f"💾 Output: {output_path}")

        command = [
    str(Path(sys.executable)), str(inference_script),
            "--checkpoint_path", str(model_path),
            "--face", str(face_image_path),
            "--audio", str(audio_path),
            "--outfile", str(output_path)
        ]

        # Run subprocess and capture output
        subprocess.run(command, check=True)

        print("✅ Lip-sync video created successfully.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Subprocess error:\n{e}")
        return False
    except Exception as ex:
        print("❌ Unexpected error in run_lipsync():")
        traceback.print_exc()
        return False
