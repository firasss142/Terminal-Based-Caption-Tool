"""Audio normalization module for forced alignment preprocessing."""

import subprocess
from pathlib import Path
from typing import Union

from config import SAMPLE_RATE


def normalize_audio(input_path: Union[str, Path], output_path: Union[str, Path]) -> str:
    """Normalize audio file to mono, 16kHz, 16-bit PCM WAV for alignment model.
    
    Converts audio from various formats (mp3, wav, m4a, aac) to the format
    required by the facebook/mms-300m forced alignment model.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    # Check if input file exists
    if not input_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {input_path}")
    
    if input_path.stat().st_size == 0:
        raise FileNotFoundError(f"Input audio file is empty: {input_path}")
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build ffmpeg command
    # -y: overwrite output file
    # -i: input file
    # -ac 1: mono (1 channel)
    # -ar: sample rate
    # -acodec pcm_s16le: 16-bit PCM
    # -f wav: WAV format
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-ac", "1",  # mono
        "-ar", str(SAMPLE_RATE),  # 16kHz sample rate
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-f", "wav",  # WAV format
        str(output_path)
    ]
    
    try:
        # Run ffmpeg with error capture
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Verify output file was created and is non-empty
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"ffmpeg failed to create output file: {output_path}")
        
        print(f"✅ Audio normalized → {output_path}")
        return str(output_path)
        
    except subprocess.CalledProcessError as e:
        error_msg = f"ffmpeg failed with return code {e.returncode}"
        if e.stderr:
            error_msg += f"\nError details: {e.stderr.strip()}"
        raise RuntimeError(error_msg)
    
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg: "
            "brew install ffmpeg (macOS) or visit https://ffmpeg.org/"
        )