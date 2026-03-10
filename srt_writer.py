"""SRT file formatting and output module for CapCut compatibility."""

from pathlib import Path
from typing import Dict, List, Union

from config import (
    SRT_ENCODING, SRT_LINE_ENDING,
    ARABIC_PARTICLES, MIN_CAPTION_DURATION_MS,
)


# ---------------------------------------------------------------------------
# Grouping helpers
# ---------------------------------------------------------------------------

def _is_latin_word(word: str) -> bool:
    """True when the word contains only non-Arabic characters (French/Latin)."""
    return bool(word) and not any("\u0600" <= c <= "\u06FF" for c in word)


def group_words(word_segments: List[Dict]) -> List[Dict]:
    """Group flat word-level segments into natural caption blocks.

    Rules applied in priority order:
    1. "و" → always group with next word.
       - If next word is "ال", make a 3-token block: و + ال + <word>.
    2. "ال" standalone → group with next word (it is the Arabic definite article).
    3. "على", "ما" → always group with next word.
    4. "ل" → if next token is a digit, group ل + digit + following noun (3-token).
    5. "ولا" → group with next if next is French/Latin OR starts with "ال" prefix.
    6. French/Latin word followed by standalone "الـ" or "ال" → group (e.g. cellulite الـ).

    All other tokens are emitted as-is.
    Post-grouping: enforce MIN_CAPTION_DURATION_MS and remove overlaps.
    """
    if not word_segments:
        return word_segments

    grouped: List[Dict] = []
    i = 0
    n = len(word_segments)

    while i < n:
        seg = word_segments[i]
        w = seg["text"]

        # ── Rule 1: "و" → always group with next ──────────────────────────
        if w == "و" and i + 1 < n:
            nxt = word_segments[i + 1]
            if nxt["text"] == "ال" and i + 2 < n:
                third = word_segments[i + 2]
                # Only make a 3-token block if the third token is a content word
                # (not a particle — e.g. "و ال و" should not collapse to 3 tokens)
                if third["text"] not in ARABIC_PARTICLES:
                    grouped.append({
                        "text": f"و ال {third['text']}",
                        "start_ms": seg["start_ms"],
                        "end_ms": third["end_ms"],
                    })
                    i += 3
                else:
                    # Fallback: 2-token "و ال"
                    grouped.append({
                        "text": f"و {nxt['text']}",
                        "start_ms": seg["start_ms"],
                        "end_ms": nxt["end_ms"],
                    })
                    i += 2
            else:
                grouped.append({
                    "text": f"و {nxt['text']}",
                    "start_ms": seg["start_ms"],
                    "end_ms": nxt["end_ms"],
                })
                i += 2
            continue

        # ── Rule 2: "ال" standalone → group with next ─────────────────────
        if w == "ال" and i + 1 < n:
            nxt = word_segments[i + 1]
            grouped.append({
                "text": f"ال {nxt['text']}",
                "start_ms": seg["start_ms"],
                "end_ms": nxt["end_ms"],
            })
            i += 2
            continue

        # ── Rule 3: "على", "ما" → always group with next ──────────────────
        if w in ("على", "ما") and i + 1 < n:
            nxt = word_segments[i + 1]
            grouped.append({
                "text": f"{w} {nxt['text']}",
                "start_ms": seg["start_ms"],
                "end_ms": nxt["end_ms"],
            })
            i += 2
            continue

        # ── Rule 4: "ل" + digit → 3-token group (ل N noun) ───────────────
        if w == "ل" and i + 1 < n:
            nxt1 = word_segments[i + 1]
            if nxt1["text"] and (nxt1["text"][0].isdigit() or nxt1["text"].isdigit()):
                if i + 2 < n:
                    nxt2 = word_segments[i + 2]
                    grouped.append({
                        "text": f"ل {nxt1['text']} {nxt2['text']}",
                        "start_ms": seg["start_ms"],
                        "end_ms": nxt2["end_ms"],
                    })
                    i += 3
                else:
                    grouped.append({
                        "text": f"ل {nxt1['text']}",
                        "start_ms": seg["start_ms"],
                        "end_ms": nxt1["end_ms"],
                    })
                    i += 2
                continue

        # ── Rule 5: "ولا" → conditional group ─────────────────────────────
        if w == "ولا" and i + 1 < n:
            nxt = word_segments[i + 1]
            nxt_text = nxt["text"]
            if _is_latin_word(nxt_text) or nxt_text.startswith("ال"):
                grouped.append({
                    "text": f"ولا {nxt_text}",
                    "start_ms": seg["start_ms"],
                    "end_ms": nxt["end_ms"],
                })
                i += 2
                continue

        # ── Rule 6: French/Latin word + trailing "الـ"/"ال" ───────────────
        if _is_latin_word(w) and i + 1 < n:
            nxt = word_segments[i + 1]
            if nxt["text"] in ("الـ", "ال"):
                grouped.append({
                    "text": f"{w} {nxt['text']}",
                    "start_ms": seg["start_ms"],
                    "end_ms": nxt["end_ms"],
                })
                i += 2
                continue

        # ── Default: emit as-is ────────────────────────────────────────────
        grouped.append(seg)
        i += 1

    # Enforce minimum duration and remove overlaps
    grouped = _enforce_timing(grouped)

    # Post-enforcement: merge blocks that are still too short (<100ms) due to tight
    # audio clusters where the audio window is physically less than 100ms.
    grouped = _merge_short_blocks(grouped, threshold_ms=MIN_CAPTION_DURATION_MS)

    # Re-index from 1
    for idx, s in enumerate(grouped):
        s["index"] = idx + 1

    return grouped


def _merge_short_blocks(segments: List[Dict], threshold_ms: int = 50) -> List[Dict]:
    """Merge blocks shorter than threshold_ms into the previous block.

    Handles tight audio clusters where a grouped token (e.g. "و ال") has
    insufficient duration.  The merged block inherits the previous block's
    start_ms and the short block's end_ms, concatenating the text.
    """
    if not segments:
        return segments
    result: List[Dict] = []
    for seg in segments:
        dur = seg["end_ms"] - seg["start_ms"]
        if dur < threshold_ms and result:
            prev = result[-1]
            result[-1] = {
                "text": f"{prev['text']} {seg['text']}",
                "start_ms": prev["start_ms"],
                "end_ms": seg["end_ms"],
            }
        else:
            result.append(dict(seg))
    return result


def _enforce_timing(segments: List[Dict]) -> List[Dict]:
    """Enforce MIN_CAPTION_DURATION_MS and eliminate gaps between captions.

    Each caption's end time matches the next caption's start time exactly.
    Overlap (end > next_start) is never allowed.
    """
    if not segments:
        return segments
    result = [dict(s) for s in segments]
    for i, seg in enumerate(result):
        if i + 1 < len(result):
            next_start = result[i + 1]["start_ms"]
            # Ensure minimum duration while eliminating gaps
            min_end = seg["start_ms"] + MIN_CAPTION_DURATION_MS
            if min_end <= next_start:
                # Set end time to match next start time exactly (no gap)
                seg["end_ms"] = next_start
            else:
                # If minimum duration would overlap next caption, clamp to 1ms before
                seg["end_ms"] = max(seg["start_ms"] + 1, next_start)
        else:
            # Last segment: just enforce minimum duration
            if seg["end_ms"] - seg["start_ms"] < MIN_CAPTION_DURATION_MS:
                seg["end_ms"] = seg["start_ms"] + MIN_CAPTION_DURATION_MS
    return result


def write_srt(segments: List[Dict], output_path: Union[str, Path],
              apply_grouping: bool = False) -> str:
    """Write aligned segments to SRT file with CapCut-compatible formatting.

    When apply_grouping=True (word-level mode) the segments are first passed
    through group_words() to merge Arabic particles with adjacent tokens before
    writing.  CRLF line endings are always enforced for CapCut compatibility.
    """
    output_path = Path(output_path)

    if not segments:
        raise ValueError("No segments provided for SRT generation")

    # Apply particle-based grouping for word-level input
    if apply_grouping:
        segments = group_words(segments)

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Validate all segments before writing
    for segment in segments:
        _validate_segment(segment)
    
    # Generate SRT content
    srt_content = []
    
    for segment in segments:
        index = segment["index"]
        text = segment["text"].strip()
        start_ms = segment["start_ms"]
        end_ms = segment["end_ms"]
        
        # Convert milliseconds to SRT timestamp format
        start_timestamp = _ms_to_srt_timestamp(start_ms)
        end_timestamp = _ms_to_srt_timestamp(end_ms)
        
        # Build SRT block
        srt_block = [
            str(index),
            f"{start_timestamp} --> {end_timestamp}",
            text,
            ""  # Empty line between blocks
        ]
        
        srt_content.extend(srt_block)
    
    # Join with CapCut-compatible line endings
    srt_text = SRT_LINE_ENDING.join(srt_content)
    
    # Write to file with UTF-8 encoding (no BOM)
    try:
        with open(output_path, 'w', encoding=SRT_ENCODING, newline='') as f:
            f.write(srt_text)
            
    except (OSError, IOError) as e:
        raise RuntimeError(f"Failed to write SRT file {output_path}: {e}")
    
    print(f"✅ SRT written → {output_path} ({len(segments)} captions)")
    return str(output_path)


def _validate_segment(segment: Dict) -> None:
    """Validate a single segment before SRT generation."""
    
    # Check required fields
    required_fields = ["index", "text", "start_ms", "end_ms"]
    for field in required_fields:
        if field not in segment:
            raise ValueError(f"Missing required field '{field}' in segment")
    
    index = segment["index"]
    text = segment["text"]
    start_ms = segment["start_ms"]
    end_ms = segment["end_ms"]
    
    # Validate index
    if not isinstance(index, int) or index < 1:
        raise ValueError(f"Invalid segment index: {index}. Must be positive integer.")
    
    # Validate text
    if not isinstance(text, str):
        raise ValueError(f"Invalid text type in segment {index}: {type(text)}. Must be string.")
    
    if not text.strip():
        raise ValueError(f"Empty text in segment {index}")
    
    # Validate timestamps
    if not isinstance(start_ms, int) or start_ms < 0:
        raise ValueError(f"Invalid start_ms in segment {index}: {start_ms}. Must be non-negative integer.")
    
    if not isinstance(end_ms, int) or end_ms < 0:
        raise ValueError(f"Invalid end_ms in segment {index}: {end_ms}. Must be non-negative integer.")
    
    if end_ms <= start_ms:
        raise ValueError(f"Invalid timestamp range in segment {index}: start={start_ms}ms, end={end_ms}ms")


def _ms_to_srt_timestamp(milliseconds: int) -> str:
    """Convert milliseconds to SRT timestamp format: HH:MM:SS,mmm"""
    
    if milliseconds < 0:
        raise ValueError(f"Negative timestamp not allowed: {milliseconds}ms")
    
    # Calculate components
    total_seconds = milliseconds // 1000
    ms = milliseconds % 1000
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    # Format with leading zeros
    # Note: SRT uses comma as decimal separator, not period
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"