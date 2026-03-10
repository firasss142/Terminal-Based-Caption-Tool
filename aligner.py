"""Forced alignment core module using ctc-forced-aligner."""

import logging
from pathlib import Path
from typing import Dict, List, Union

from config import (
    MIN_CAPTION_DURATION_MS, 
    GAP_BETWEEN_CAPTIONS_MS
)

# Set up logging for this module
logger = logging.getLogger(__name__)


def align(audio_path: Union[str, Path], sentences: List[str], language: str = "ara") -> List[Dict]:
    """Perform forced alignment on audio with provided sentences.
    
    Uses the ctc-forced-aligner library to align text sentences with audio 
    timestamps. Returns precise millisecond timestamps suitable for SRT generation.
    """
    try:
        # Import alignment library
        from ctc_forced_aligner import AlignmentTorchSingleton
        import tempfile
        import ssl
        import urllib.request
        
        # Fix SSL certificate issues on macOS
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # Apply the SSL context globally for urllib
        original_urlopen = urllib.request.urlopen
        def patched_urlopen(url, *args, **kwargs):
            kwargs.setdefault('context', ctx)
            return original_urlopen(url, *args, **kwargs)
        urllib.request.urlopen = patched_urlopen
        
    except ImportError as e:
        raise RuntimeError(
            f"Required alignment libraries not installed: {e}\n"
            "Install with: pip install ctc-forced-aligner torch torchaudio"
        )
    
    audio_path = Path(audio_path)
    
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    if not sentences:
        raise ValueError("No sentences provided for alignment")
    
    # Clean sentences - remove empty ones
    clean_sentences = [s.strip() for s in sentences if s.strip()]
    if not clean_sentences:
        raise ValueError("No non-empty sentences provided for alignment")
    
    logger.info(f"Starting alignment for {len(clean_sentences)} sentences")
    
    # Create a temporary text file with the script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        script_text = '\n'.join(clean_sentences)
        f.write(script_text)
        temp_script_path = f.name
    
    try:
        print("📥 Downloading alignment model (first run only)...")
        
        # Create alignment instance (singleton pattern - downloads model on first use)
        aligner = AlignmentTorchSingleton()
        
        # Create temporary output SRT file
        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as f:
            temp_srt_path = f.name
        
        # Perform alignment using the built-in SRT generation with MMS_FA model
        success = aligner.generate_srt(
            input_audio_path=str(audio_path),
            input_text_path=temp_script_path,
            output_srt_path=temp_srt_path,
            model_type='MMS_FA'  # Use facebook/mms-300m model
        )
        
        if not success:
            raise RuntimeError("Alignment failed - no SRT file generated")
        
        # Parse the generated SRT to extract our format
        segments = _parse_generated_srt(temp_srt_path)
        
        # Clean up temp files
        Path(temp_script_path).unlink(missing_ok=True)
        Path(temp_srt_path).unlink(missing_ok=True)
        
    except Exception as e:
        # Clean up temp files on error
        Path(temp_script_path).unlink(missing_ok=True)
        try:
            Path(temp_srt_path).unlink(missing_ok=True)
        except:
            pass
        raise RuntimeError(f"Forced alignment failed: {e}")
    
    # Apply smart gap correction
    segments = _apply_smart_gap_correction(segments)
    
    logger.info(f"Alignment completed: {len(segments)} segments")
    return segments


def align_word_level(audio_path: Union[str, Path], sentences: List[str],
                    language: str = "ara", max_chars: int = 42) -> List[Dict]:
    """Perform true word-level forced alignment using facebook/mms-300m (MMS_FA).

    Arabic text is romanised with unidecode so the MMS_FA CTC model can align
    every word — Arabic, French and mixed tokens alike — at word granularity.
    Original script text is preserved unchanged in the output.

    Returns a flat list of per-word dicts (grouped later by srt_writer.group_words):
        [{"index": 1, "text": "كنت", "start_ms": 0, "end_ms": 300}, ...]
    """
    try:
        import torch
        import torchaudio
        import torchaudio.functional as F
        from unidecode import unidecode
        from ctc_forced_aligner import (
            load_audio as cfa_load_audio,
            align as cfa_align,
            unflatten,
            _postprocess_results,
        )
    except ImportError as e:
        raise RuntimeError(
            f"Required libraries not installed: {e}\n"
            "Install with: pip install ctc-forced-aligner torch torchaudio"
        )

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    clean_sentences = [s.strip() for s in sentences if s.strip()]
    if not clean_sentences:
        raise ValueError("No non-empty sentences provided for alignment")

    logger.info(f"Starting word-level alignment: {len(clean_sentences)} sentences")

    full_text = " ".join(clean_sentences)
    original_words = full_text.split()

    print("📥 Loading facebook/mms-300m model (cached after first run)...")
    device = torch.device("cpu")
    bundle = torchaudio.pipelines.MMS_FA
    dictionary = bundle.get_dict(star=None)
    model = bundle.get_model(with_star=False).to(device)

    waveform = cfa_load_audio(str(audio_path), ret_type="torch").to(device)

    print("🔊 Generating CTC emissions...")
    with torch.inference_mode():
        emission, _ = model(waveform)

    # Romanise each script word via unidecode, then filter to MMS_FA phoneme set.
    # Arabic "كنت" → "knt",  French "cellulite" → "cellulite",  "100%" → ""
    romanized = [unidecode(w).lower() for w in original_words]
    cleaned = [
        "".join(c for c in rom if c in dictionary and dictionary[c] != 0)
        for rom in romanized
    ]

    # Build aligned transcript and a map back to original word positions
    transcript: List[str] = []
    pos_map: List[int] = []          # pos_map[i] = original_words index
    for orig_idx, cw in enumerate(cleaned):
        if cw:
            transcript.append(cw)
            pos_map.append(orig_idx)

    if not transcript:
        raise RuntimeError("All script words were filtered during romanisation")

    print(f"🔗 Running forced alignment ({len(transcript)} tokens)...")
    tokenized = [
        dictionary[c]
        for word in transcript
        for c in word
        if c in dictionary and dictionary[c] != 0
    ]
    aligned_tokens, alignment_scores = cfa_align(emission, tokenized, device)
    token_spans = F.merge_tokens(aligned_tokens[0], alignment_scores[0])
    word_spans = unflatten(token_spans, [len(w) for w in transcript])
    word_ts = _postprocess_results(
        transcript, word_spans, waveform,
        emission.size(1), bundle.sample_rate, alignment_scores
    )
    # word_ts[i]: {"start": sec, "end": sec, "text": cleaned_word}

    # Map aligned timestamps back to original words by position
    ts_by_orig: Dict[int, Dict] = {pos_map[i]: word_ts[i] for i in range(len(pos_map))}

    word_segments: List[Dict] = []
    for orig_idx, orig_word in enumerate(original_words):
        if orig_idx in ts_by_orig:
            wt = ts_by_orig[orig_idx]
            word_segments.append({
                "index": orig_idx + 1,
                "text": orig_word,
                "start_ms": int(wt["start"] * 1000),
                "end_ms": int(wt["end"] * 1000),
            })
        else:
            # Word had no phoneme tokens (e.g. "100%") — place after prev word
            prev_end = word_segments[-1]["end_ms"] if word_segments else 0
            word_segments.append({
                "index": orig_idx + 1,
                "text": orig_word,
                "start_ms": prev_end,
                "end_ms": prev_end + MIN_CAPTION_DURATION_MS,
            })

    word_segments = _apply_smart_gap_correction(word_segments)
    for i, seg in enumerate(word_segments):
        seg["index"] = i + 1

    logger.info(f"Word-level alignment completed: {len(word_segments)} words")
    return word_segments


def _parse_generated_srt(srt_path: str) -> List[Dict]:
    """Parse SRT file generated by ctc-forced-aligner into our format."""
    
    segments = []
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # Split by double newlines to get SRT blocks
    blocks = [block.strip() for block in content.split('\n\n') if block.strip()]
    
    for block in blocks:
        lines = block.split('\n')
        if len(lines) < 3:
            continue
            
        try:
            # Parse SRT block
            index = int(lines[0])
            
            # Parse timestamp line: "00:00:01,234 --> 00:00:02,567"
            timestamp_line = lines[1]
            start_str, end_str = timestamp_line.split(' --> ')
            
            start_ms = _srt_time_to_ms(start_str)
            end_ms = _srt_time_to_ms(end_str)
            
            # Get text (may be multiple lines)
            text = '\n'.join(lines[2:]).strip()
            
            segment = {
                "index": index,
                "text": text,
                "start_ms": start_ms,
                "end_ms": end_ms
            }
            
            segments.append(segment)
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse SRT block: {block[:50]}... Error: {e}")
            continue
    
    return segments


def _srt_time_to_ms(time_str: str) -> int:
    """Convert SRT time format (HH:MM:SS,mmm) to milliseconds."""
    # Format: "00:00:01,234"
    time_part, ms_part = time_str.split(',')
    hours, minutes, seconds = map(int, time_part.split(':'))
    
    total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + int(ms_part)
    return total_ms


def _apply_smart_gap_correction(segments: List[Dict]) -> List[Dict]:
    """Apply smart gap correction to prevent overlapping captions.
    
    If consecutive captions overlap (end_ms[i] > start_ms[i+1]):
    - Set end_ms[i] = start_ms[i+1] - GAP_BETWEEN_CAPTIONS_MS
    - Log which segments were corrected
    """
    
    if len(segments) <= 1:
        return segments
    
    corrected_segments = segments.copy()
    corrections_made = 0
    
    for i in range(len(corrected_segments) - 1):
        current = corrected_segments[i]
        next_segment = corrected_segments[i + 1]
        
        if current["end_ms"] > next_segment["start_ms"]:
            # Calculate new end time with gap
            new_end_ms = next_segment["start_ms"] - GAP_BETWEEN_CAPTIONS_MS
            
            # Ensure minimum caption duration
            min_end_ms = current["start_ms"] + MIN_CAPTION_DURATION_MS
            
            if new_end_ms < min_end_ms:
                # If corrected end would be too short, adjust next segment start instead
                next_segment["start_ms"] = min_end_ms + GAP_BETWEEN_CAPTIONS_MS
                current["end_ms"] = min_end_ms
            else:
                current["end_ms"] = new_end_ms
            
            logger.debug(f"Corrected overlap between segments {i+1} and {i+2}")
            corrections_made += 1
    
    if corrections_made > 0:
        logger.info(f"Smart gap correction applied to {corrections_made} segment pairs")
    
    return corrected_segments