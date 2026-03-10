"""Input validation module for audio and script files."""

import subprocess
from pathlib import Path
from typing import Dict, Union

from config import MIN_WORDS_PER_MINUTE, MAX_WORDS_PER_MINUTE, MISMATCH_THRESHOLD


def validate_inputs(audio_path: Union[str, Path], script_path: Union[str, Path]) -> Dict:
    """Validate audio and script files before processing.
    
    Performs comprehensive pre-flight checks including file existence,
    content validation, and duration/word count sanity checks for 
    Tunisian Arabic content.
    """
    audio_path = Path(audio_path)
    script_path = Path(script_path)
    warnings = []
    
    # Check audio file exists and is non-empty
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    if audio_path.stat().st_size == 0:
        raise ValueError(f"Audio file is empty: {audio_path}")
    
    # Check script file exists and is non-empty
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")
    
    if script_path.stat().st_size == 0:
        raise ValueError(f"Script file is empty: {script_path}")
    
    # Validate script encoding and content
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
    except UnicodeDecodeError:
        raise ValueError(f"Script file must be UTF-8 encoded: {script_path}")
    
    if not script_content.strip():
        raise ValueError(f"Script file contains no text: {script_path}")
    
    # Parse script into sentences (non-empty lines)
    sentences = [line.strip() for line in script_content.splitlines() if line.strip()]
    
    if len(sentences) == 0:
        raise ValueError(f"Script file contains no non-empty lines: {script_path}")
    
    # Count words in script
    # For Tunisian Arabic: count Arabic words, Latin words, and numbers
    word_count = 0
    for sentence in sentences:
        # Split on whitespace and count non-empty tokens
        # This handles mixed Arabic/French/numbers appropriately
        tokens = sentence.split()
        word_count += len([token for token in tokens if token.strip()])
    
    # Get audio duration using ffprobe
    try:
        audio_duration_sec = _get_audio_duration(audio_path)
    except Exception as e:
        raise RuntimeError(f"Failed to analyze audio duration: {e}")
    
    # Validate duration/word count ratio for Tunisian Arabic
    if audio_duration_sec > 0:
        words_per_minute = (word_count / audio_duration_sec) * 60
        
        if words_per_minute < MIN_WORDS_PER_MINUTE:
            pct_diff = ((MIN_WORDS_PER_MINUTE - words_per_minute) / MIN_WORDS_PER_MINUTE) * 100
            if pct_diff > (MISMATCH_THRESHOLD * 100):
                warnings.append(
                    f"Script may be too short for audio duration. "
                    f"Expected ≥{MIN_WORDS_PER_MINUTE} words/min, got {words_per_minute:.1f} "
                    f"({pct_diff:.1f}% below minimum)"
                )
        
        elif words_per_minute > MAX_WORDS_PER_MINUTE:
            pct_diff = ((words_per_minute - MAX_WORDS_PER_MINUTE) / MAX_WORDS_PER_MINUTE) * 100
            if pct_diff > (MISMATCH_THRESHOLD * 100):
                warnings.append(
                    f"Script may be too long for audio duration. "
                    f"Expected ≤{MAX_WORDS_PER_MINUTE} words/min, got {words_per_minute:.1f} "
                    f"({pct_diff:.1f}% above maximum)"
                )
    
    return {
        "audio_duration_sec": audio_duration_sec,
        "sentence_count": len(sentences),
        "word_count": word_count,
        "warnings": warnings
    }


def _get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", 
        "format=duration", "-of", "csv=p=0", str(audio_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration_str = result.stdout.strip()
        
        if not duration_str:
            raise ValueError("ffprobe returned empty duration")
        
        return float(duration_str)
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed: {e.stderr}")
    
    except ValueError as e:
        raise RuntimeError(f"Failed to parse audio duration: {e}")
    
    except FileNotFoundError:
        raise RuntimeError(
            "ffprobe not found. Please install ffmpeg: "
            "brew install ffmpeg (macOS) or visit https://ffmpeg.org/"
        )