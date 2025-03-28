# modules/video_creator.py

import os
from moviepy.editor import ImageClip, AudioFileClip
from modules.lipsync import run_lipsync

def create_video(image_path, audio_path, output_folder="static/output", lip_sync=False):
    try:
        print("🎬 Starting video generation...")

        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)

        if lip_sync:
            print("🔄 Lip sync enabled: using Wav2Lip...")
            # Run Wav2Lip processing
            output_path = os.path.join(output_folder, "final_lipsync_video.mp4")
            result = run_lipsync(image_path, audio_path, output_path)
            return {
                "status": "success" if result else "error",
                "video_path": output_path if result else None,
                "message": None if result else "Lip-sync failed"
            }

        else:
            print("📸 Generating video using MoviePy...")

            # Load audio
            audio_clip = AudioFileClip(audio_path)
            image_clip = ImageClip(image_path).set_duration(audio_clip.duration)

            # Combine image and audio
            final_clip = image_clip.set_audio(audio_clip)

            # Resize to square (optional)
            final_clip = final_clip.resize(height=1080)

            # Save video
            output_path = os.path.join(output_folder, "final_video.mp4")
            final_clip.write_videofile(output_path, fps=24)

            return {
                "status": "success",
                "video_path": output_path
            }

    except Exception as e:
        print("❌ Error creating video:", e)
        return {
            "status": "error",
            "message": str(e)
        }
