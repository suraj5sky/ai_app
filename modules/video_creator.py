# modules/video_creator.py

import os
import time
import logging
import psutil
from moviepy.editor import ImageClip, AudioFileClip
from modules.lipsync import run_lipsync
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

logger = logging.getLogger(__name__)

def is_valid_video(filepath):
    """Check if video file exists and has minimum size"""
    return os.path.exists(filepath) and os.path.getsize(filepath) > 1024  # >1KB

def create_video(image_path, audio_path, output_folder="static/output", lip_sync=False, timeout=300):
    try:
        logger.info("🎬 Starting video generation...")
        logger.info(f"System load: {psutil.cpu_percent()}% CPU | {psutil.virtual_memory().percent}% RAM")

        # Validate inputs and output directory
        if not all([os.path.exists(image_path), os.path.exists(audio_path)]):
            return {"status": "error", "message": "Missing input files"}
        
        os.makedirs(output_folder, exist_ok=True)
        try:
            test_file = os.path.join(output_folder, '.permission_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            return {"status": "error", "message": f"Output folder not writable: {str(e)}"}

        def _generate_video_content():
            if lip_sync:
                logger.info("🔄 Lip sync enabled: using Wav2Lip...")
                output_path = os.path.join(output_folder, f"lipsync_{int(time.time())}.mp4")
                result = run_lipsync(image_path, audio_path, output_path)
                
                if not result or not is_valid_video(output_path):
                    return {"status": "error", "message": "Lip-sync failed", "video_path": None}
                return {"status": "success", "video_path": output_path}
                
            else:
                logger.info("📸 Generating video using MoviePy...")
                try:
                    audio_clip = AudioFileClip(audio_path)
                    image_clip = ImageClip(image_path).set_duration(audio_clip.duration)
                    final_clip = image_clip.set_audio(audio_clip).resize(height=1080)
                    output_path = os.path.join(output_folder, f"video_{int(time.time())}.mp4")
                    final_clip.write_videofile(output_path, fps=24, logger=None)  # Disable MoviePy logs
                    
                    if not is_valid_video(output_path):
                        return {"status": "error", "message": "Generated video is invalid"}
                    return {"status": "success", "video_path": output_path}
                    
                finally:
                    for clip in ['audio_clip', 'image_clip', 'final_clip']:
                        if clip in locals():
                            locals()[clip].close()

        # Thread-based timeout wrapper
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_generate_video_content)
            try:
                result = future.result(timeout=timeout)
                logger.info(f"✅ Video generation completed: {result}")
                return result
            except FutureTimeoutError:
                logger.error(f"❌ Video generation timed out after {timeout} seconds")
                return {"status": "error", "message": f"Operation timed out after {timeout} seconds"}

    except Exception as e:
        logger.error(f"❌ Video generation failed: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}