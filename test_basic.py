#!/usr/bin/env python3
"""Basic test script for the SRT Caption Generator modules."""

import tempfile
from pathlib import Path
from validator import validate_inputs
from normalize import normalize_audio
from srt_writer import write_srt

def test_basic_functionality():
    """Test basic functionality without requiring alignment model."""
    
    print("🧪 Testing SRT Caption Generator modules...")
    
    # Test files
    input_dir = Path("input")
    test_audio = input_dir / "test_audio.wav"
    test_script = input_dir / "test_script.txt"
    
    if not test_audio.exists():
        print("❌ Test audio file not found. Run: ffmpeg -f lavfi -i \"sine=frequency=440:duration=3\" -ar 16000 -ac 1 input/test_audio.wav")
        return False
    
    if not test_script.exists():
        print("❌ Test script file not found")
        return False
    
    try:
        # Test 1: Validation
        print("  Testing validator...")
        result = validate_inputs(test_audio, test_script)
        print(f"    ✅ Validation: {result['audio_duration_sec']:.1f}s, {result['sentence_count']} sentences")
        
        # Test 2: Audio normalization
        print("  Testing audio normalization...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_path = tmp.name
        
        normalized_path = normalize_audio(test_audio, temp_path)
        print(f"    ✅ Normalization: {Path(normalized_path).name}")
        
        # Test 3: SRT writing (with dummy data)
        print("  Testing SRT writer...")
        test_segments = [
            {
                "index": 1,
                "text": "هذا اختبار للنظام",
                "start_ms": 0,
                "end_ms": 1000
            },
            {
                "index": 2, 
                "text": "This is a system test",
                "start_ms": 1050,
                "end_ms": 2000
            },
            {
                "index": 3,
                "text": "C'est un test du système",
                "start_ms": 2050,
                "end_ms": 3000
            }
        ]
        
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        srt_path = write_srt(test_segments, output_dir / "test_output.srt")
        print(f"    ✅ SRT generation: {Path(srt_path).name}")
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
        
        print("\n🎉 Basic functionality tests passed!")
        print("🔧 To test full alignment pipeline:")
        print("   1. Install: pip install ctc-forced-aligner torch torchaudio")
        print("   2. Run: python3 align.py --audio input/test_audio.wav --script input/test_script.txt")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_basic_functionality()