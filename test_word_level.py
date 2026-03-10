#!/usr/bin/env python3
"""STEP 1 — Verify word-level alignment for Arabic+French text.

Tests align_word_level() (MMS_FA + unidecode) on the first N sentences.
Run: .venv/bin/python test_word_level.py
"""

import sys
import tempfile
from pathlib import Path

AUDIO_PATH = Path("input/biovera-vo-1.MP3.MP3")
SCRIPT_PATH = Path("input/second.txt")
SENTENCES_TO_TEST = 3  # Only first N sentences for speed


def main():
    if not AUDIO_PATH.exists():
        print(f"❌ Audio not found: {AUDIO_PATH}")
        sys.exit(1)
    if not SCRIPT_PATH.exists():
        print(f"❌ Script not found: {SCRIPT_PATH}")
        sys.exit(1)

    # 1. Normalize audio
    print("Normalizing audio...")
    from normalize import normalize_audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    normalize_audio(AUDIO_PATH, wav_path)

    # 2. Load first N sentences
    with open(SCRIPT_PATH, encoding="utf-8") as f:
        all_lines = [l.strip() for l in f if l.strip()]
    sentences = all_lines[:SENTENCES_TO_TEST]
    print(f"\nTesting on {len(sentences)} sentences:")
    for i, s in enumerate(sentences):
        print(f"  {i+1}: {s}")

    # 3. Run word-level alignment
    print("\nRunning align_word_level (MMS_FA + unidecode)...")
    from aligner import align_word_level
    word_segments = align_word_level(wav_path, sentences)

    full_text = " ".join(sentences)
    original_words = full_text.split()

    print(f"\nWord timestamps count   : {len(word_segments)}")
    print(f"Original word count     : {len(original_words)}")
    print(f"Count match             : {len(word_segments) == len(original_words)}")

    print("\n--- WORD TIMESTAMPS ---")
    for wt in word_segments:
        dur_ms = wt["end_ms"] - wt["start_ms"]
        print(f"  {wt['index']:3d}: {wt['start_ms']:6d}-{wt['end_ms']:6d}ms "
              f"({dur_ms:4d}ms) | '{wt['text']}'")

    # 4. Sanity checks
    print("\n--- SANITY CHECKS ---")
    if word_segments:
        first_start = word_segments[0]["start_ms"]
        last_end = word_segments[-1]["end_ms"]
        print(f"First word start : {first_start}ms (expect ~0ms)")
        print(f"Last word end    : {last_end}ms")
        overlaps = sum(
            1 for i in range(len(word_segments) - 1)
            if word_segments[i]["end_ms"] > word_segments[i + 1]["start_ms"]
        )
        print(f"Overlaps         : {overlaps} (expect 0)")
        short = sum(1 for w in word_segments if w["end_ms"] - w["start_ms"] < 100)
        print(f"<100ms durations : {short} (expect 0)")

    # Cleanup
    Path(wav_path).unlink(missing_ok=True)
    print("\nDone.")


if __name__ == "__main__":
    main()
