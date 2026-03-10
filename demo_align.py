#!/usr/bin/env python3
"""Demo version of SRT Caption Generator using simulated alignment data.

This demonstrates the full pipeline without requiring model downloads.
For production use, install the alignment libraries as shown in README.md
"""

import sys
import tempfile
from pathlib import Path
from typing import Dict, List

# Import all our modules
from config import DEFAULT_LANGUAGE, MAX_CHARS_PER_LINE
from validator import validate_inputs
from normalize import normalize_audio
from srt_writer import write_srt


def demo_align(audio_path: str, sentences: List[str], language: str = "ara") -> List[Dict]:
    """Demo version of forced alignment using simulated timing data."""
    
    print("🔧 Demo mode: Using simulated alignment data")
    print("   For real alignment, install: pip install ctc-forced-aligner torch torchaudio")
    
    # Simulate realistic timing for our test sentences
    segments = []
    total_duration_ms = 3000  # 3 seconds from our test audio
    
    # Distribute time across sentences
    time_per_sentence = total_duration_ms // len(sentences)
    
    for i, sentence in enumerate(sentences):
        start_ms = i * time_per_sentence
        end_ms = start_ms + time_per_sentence
        
        # Add some realistic variation
        if i == len(sentences) - 1:
            end_ms = total_duration_ms  # Last sentence gets remaining time
        
        segment = {
            "index": i + 1,
            "text": sentence.strip(),
            "start_ms": start_ms,
            "end_ms": end_ms
        }
        segments.append(segment)
    
    # Add 50ms gap between segments (simulating smart gap correction)
    for i in range(len(segments) - 1):
        segments[i]["end_ms"] -= 25
        segments[i + 1]["start_ms"] = segments[i]["end_ms"] + 50
    
    return segments


def main():
    """Demo main function showing the full pipeline."""
    
    # Test files
    audio_file = "input/test_audio.wav"
    script_file = "input/test_script.txt"
    output_file = "output/demo_output.srt"
    
    if not Path(audio_file).exists() or not Path(script_file).exists():
        print("❌ Demo files not found. Run the basic test first:")
        print("   python3 test_basic.py")
        sys.exit(1)
    
    print("🎬 SRT Caption Generator Demo")
    print(f"📂 Input: {audio_file} + {script_file}")
    
    try:
        # Step 1: Validation
        print("🔍 Validating inputs...")
        validation = validate_inputs(audio_file, script_file)
        
        for warning in validation["warnings"]:
            print(f"⚠️  {warning}")
        
        print(f"📊 Audio: {validation['audio_duration_sec']:.1f}s, "
              f"Script: {validation['sentence_count']} sentences, "
              f"{validation['word_count']} words")
        
        # Step 2: Audio normalization
        print("🔊 Normalizing audio...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_wav = tmp.name
        
        try:
            normalize_audio(audio_file, temp_wav)
            
            # Step 3: Load script
            print("📝 Loading script...")
            with open(script_file, 'r', encoding='utf-8') as f:
                script_content = f.read()
            
            sentences = [line.strip() for line in script_content.splitlines() if line.strip()]
            print(f"📋 Found {len(sentences)} sentences for alignment")
            
            # Step 4: Demo alignment
            print("🤖 Performing demo forced alignment...")
            segments = demo_align(temp_wav, sentences)
            
            # Step 5: Write SRT
            print("💾 Writing SRT file...")
            Path("output").mkdir(exist_ok=True)
            srt_path = write_srt(segments, output_file)
            
            # Step 6: Results
            duration = validation['audio_duration_sec']
            print(f"🎬 Demo complete! {len(segments)} captions | Duration: {duration:.1f}s")
            print(f"📄 Output: {srt_path}")
            
            # Show alignment details
            print("\n📋 Alignment details:")
            for segment in segments:
                start_sec = segment["start_ms"] / 1000
                end_sec = segment["end_ms"] / 1000
                text = segment["text"][:40] + ("..." if len(segment["text"]) > 40 else "")
                print(f"  {segment['index']:2d}: {start_sec:5.2f}-{end_sec:5.2f}s | {text}")
            
            # Show SRT format
            print(f"\n📖 Generated SRT preview:")
            with open(srt_path, 'r', encoding='utf-8') as f:
                preview = f.read()[:400]
                print(preview + ("..." if len(preview) == 400 else ""))
            
            print(f"\n✅ Perfect! This SRT file can be imported directly into CapCut.")
            print(f"🔧 For real alignment, follow the installation instructions in README.md")
            
        finally:
            # Cleanup
            Path(temp_wav).unlink(missing_ok=True)
            
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()