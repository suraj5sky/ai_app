import os
import subprocess
import logging
from pathlib import Path
import traceback
import sys
from moviepy.editor import ImageClip
from utils.path_manager import path_manager
from typing import Union, Tuple

logger = logging.getLogger(__name__)

# Constants
MIN_VIDEO_SIZE = 1024  # 1KB minimum file size
TEMP_FILE_PREFIX = "temp_wav2lip_"

def is_image_file(filepath: Union[str, Path]) -> bool:
    """Check if file is an image with case-insensitive extension check."""
    return Path(filepath).suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}

def is_video_file(filepath: Union[str, Path]) -> bool:
    """Check if file is a video with case-insensitive extension check."""
    return Path(filepath).suffix.lower() in {'.mp4', '.avi', '.mov', '.mkv', '.webm'}

def validate_media_file(filepath: Path) -> Tuple[bool, str]:
    """Validate media file exists and is accessible."""
    try:
        if not filepath.exists():
            return False, f"File not found: {filepath}"
        if not os.access(filepath, os.R_OK):
            return False, f"File not readable: {filepath}"
        if filepath.stat().st_size == 0:
            return False, f"Empty file: {filepath}"
        return True, ""
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def convert_image_to_video(
    image_path: Union[str, Path],
    output_path: Union[str, Path],
    duration: int = 5,
    fps: int = 25
) -> Tuple[bool, str]:
    """Convert image to video clip with error handling and validation."""
    try:
        image_path = path_manager.resolve_path(image_path)
        output_path = path_manager.resolve_path(output_path)

        # Validate input
        valid, msg = validate_media_file(image_path)
        if not valid:
            return False, msg

        logger.info(f"Converting image to video: {image_path} -> {output_path}")
        
        # Create video clip
        clip = ImageClip(str(image_path)).set_duration(duration)
        clip.write_videofile(
            str(output_path),
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            threads=4,
            logger=None,
            preset='fast',
            verbose=False
        )

        # Verify output
        if not validate_media_file(output_path)[0]:
            return False, "Output video creation failed"
            
        logger.info(f"Image conversion successful: {output_path}")
        return True, ""
        
    except Exception as e:
        error_msg = f"Image-to-video failed: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return False, error_msg

def run_lipsync(
    face_path: Union[str, Path],
    audio_path: Union[str, Path],
    output_path: Union[str, Path],
    wav2lip_model_path: Union[str, Path] = "models/wav2lip.pth",
    timeout: int = 300,
    resize_factor: int = 1,
    fps: int = 25,
    cleanup: bool = True
) -> Tuple[bool, str]:
    """
    Enhanced Wav2Lip execution with comprehensive error handling.
    
    Returns tuple of (success: bool, error_message: str)
    """
    temp_video_path = None
    try:
        # Resolve and validate all paths
        face_path = path_manager.resolve_path(face_path)
        audio_path = path_manager.resolve_path(audio_path)
        output_path = path_manager.resolve_path(output_path)
        wav2lip_model_path = path_manager.resolve_path(wav2lip_model_path)

        # Input validation
        for path, name in [(face_path, "Face"), (audio_path, "Audio"), 
                          (wav2lip_model_path, "Model")]:
            valid, msg = validate_media_file(path)
            if not valid:
                return False, f"{name} validation failed: {msg}"

        # Determine input type
        input_is_image = is_image_file(face_path)
        input_is_video = is_video_file(face_path)
        
        if not (input_is_image or input_is_video):
            error_msg = "Input must be image (PNG/JPG/WebP) or video (MP4/AVI/MOV)"
            logger.error(error_msg)
            return False, error_msg

        # Handle image input
        if input_is_image:
            temp_video_path = path_manager.get_path(
                output_path.parent,
                f"{TEMP_FILE_PREFIX}{face_path.stem}.mp4",
                ensure_exists=True
            )
            success, error_msg = convert_image_to_video(
                face_path, temp_video_path, duration=5, fps=fps
            )
            if not success:
                return False, error_msg
            face_media_path = temp_video_path
            static_flag = ["--static"]
        else:
            face_media_path = face_path
            static_flag = []

        # Build Wav2Lip command
        command = [
            sys.executable,
            str(path_manager.get_path("Wav2Lip", "inference.py")),
            "--checkpoint_path", str(wav2lip_model_path),
            "--face", str(face_media_path),
            "--audio", str(audio_path),
            "--outfile", str(output_path),
            "--resize_factor", str(resize_factor),
            "--fps", str(fps),
            *static_flag,
            "--pads", "0", "10", "0", "0",
            "--nosmooth",
            "--preprocess", "crop"  # Auto-crop to face
        ]

        logger.info(f"Executing Wav2Lip with command: {' '.join(command)}")

        # Execute with resource monitoring
        result = subprocess.run(
            command,
            timeout=timeout,
            check=True,
            capture_output=True,
            text=True,
            cwd=str(path_manager.get_path("Wav2Lip")),
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        # Output validation
        if not validate_media_file(output_path)[0]:
            error_msg = "Output file validation failed"
            logger.error(error_msg)
            return False, error_msg

        logger.info(f"Lip-sync completed successfully. Output: {output_path}")
        return True, ""

    except subprocess.TimeoutExpired:
        error_msg = f"Process timed out after {timeout} seconds"
        logger.error(error_msg)
        return False, error_msg
        
    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Wav2Lip failed (code {e.returncode}):\n"
            f"STDERR: {e.stderr.strip() or 'None'}\n"
            f"STDOUT: {e.stdout.strip() or 'None'}"
        )
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return False, error_msg
        
    finally:
        # Cleanup temporary files
        if cleanup and temp_video_path and isinstance(temp_video_path, Path):
            try:
                if temp_video_path.exists():
                    temp_video_path.unlink(missing_ok=True)
                    logger.debug(f"Cleaned up temp file: {temp_video_path}")
            except Exception as e:
                logger.warning(f"Temp file cleanup failed: {str(e)}")