"""Batch processing module for multiple audio/script file pairs."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import tempfile

from config import DEFAULT_LANGUAGE
from validator import validate_inputs
from normalize import normalize_audio
from aligner import align  
from srt_writer import write_srt

logger = logging.getLogger(__name__)


def batch_process(input_dir: Union[str, Path], output_dir: Union[str, Path], 
                 language: str = DEFAULT_LANGUAGE) -> None:
    """Process all matched audio/script file pairs in input directory.
    
    Scans input directory for audio files, matches them with corresponding
    text files by filename stem, and processes each pair through the full
    alignment pipeline. Generates processing log with detailed results.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    
    # Validate directories
    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(f"Input directory does not exist: {input_dir}")
    
    # Create output directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all audio/script pairs
    pairs = find_audio_script_pairs(input_dir)
    
    if not pairs:
        print(f"❌ No audio/script pairs found in {input_dir}")
        print("Expected pairs like: video_01.mp3 ↔ video_01.txt")
        return
    
    print(f"🎬 Found {len(pairs)} audio/script pairs to process")
    print(f"📂 Input: {input_dir}")
    print(f"📂 Output: {output_dir}")
    print()
    
    # Process each pair
    results = []
    
    for i, (audio_path, script_path) in enumerate(pairs, 1):
        print(f"Processing {i}/{len(pairs)}: {audio_path.name}...")
        
        try:
            result = process_single_pair(
                audio_path, script_path, output_dir, language, i, len(pairs)
            )
            results.append(result)
            print(f"✅ {audio_path.stem}: {result['caption_count']} captions, {result['duration_sec']:.1f}s")
            
        except Exception as e:
            error_result = {
                "filename": audio_path.stem,
                "status": "failed",
                "error": str(e),
                "caption_count": 0,
                "duration_sec": 0.0
            }
            results.append(error_result)
            print(f"❌ {audio_path.stem}: {e}")
        
        print()  # Empty line between files
    
    # Generate processing log
    generate_processing_log(output_dir, results)
    
    # Print summary
    print_batch_summary(results)


def find_audio_script_pairs(input_dir: Path) -> List[Tuple[Path, Path]]:
    """Find matching audio and script file pairs in input directory."""
    
    # Supported audio extensions
    audio_extensions = {'.mp3', '.wav', '.m4a', '.aac'}
    
    # Find all audio files
    audio_files = []
    for ext in audio_extensions:
        audio_files.extend(input_dir.glob(f"*{ext}"))
    
    # Match with corresponding text files
    pairs = []
    
    for audio_path in audio_files:
        script_path = input_dir / f"{audio_path.stem}.txt"
        
        if script_path.exists():
            pairs.append((audio_path, script_path))
        else:
            logger.warning(f"No matching script file for {audio_path.name}")
    
    # Sort pairs by filename for consistent processing order
    pairs.sort(key=lambda x: x[0].name)
    
    return pairs


def process_single_pair(audio_path: Path, script_path: Path, output_dir: Path,
                       language: str, current: int, total: int) -> Dict:
    """Process a single audio/script pair through the full pipeline."""
    
    # Determine output path
    output_filename = f"{audio_path.stem}.srt"
    output_path = output_dir / output_filename
    
    # Step 1: Validate inputs
    validation_result = validate_inputs(audio_path, script_path)
    
    # Step 2: Normalize audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        temp_wav_path = tmp_file.name
    
    try:
        normalize_audio(audio_path, temp_wav_path)
        
        # Step 3: Load script
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        sentences = [line.strip() for line in script_content.splitlines() if line.strip()]
        
        if not sentences:
            raise ValueError(f"No non-empty lines found in script")
        
        # Step 4: Perform alignment
        segments = align(temp_wav_path, sentences, language)
        
        # Step 5: Write SRT file
        write_srt(segments, output_path)
        
        # Return success result
        return {
            "filename": audio_path.stem,
            "status": "success",
            "caption_count": len(segments),
            "duration_sec": validation_result["audio_duration_sec"],
            "output_path": str(output_path),
            "warnings": validation_result["warnings"]
        }
        
    finally:
        # Clean up temporary WAV file
        try:
            Path(temp_wav_path).unlink()
        except OSError:
            pass


def generate_processing_log(output_dir: Path, results: List[Dict]) -> None:
    """Generate detailed processing log file."""
    
    log_path = output_dir / "processing_log.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"SRT Caption Generator - Batch Processing Log\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Processed: {len(results)} files\n")
        f.write("=" * 60 + "\n\n")
        
        for result in results:
            status_icon = "✅" if result["status"] == "success" else "❌"
            f.write(f"{status_icon} {result['filename']}\n")
            f.write(f"   Status: {result['status']}\n")
            
            if result["status"] == "success":
                f.write(f"   Captions: {result['caption_count']}\n")
                f.write(f"   Duration: {result['duration_sec']:.1f}s\n")
                f.write(f"   Output: {Path(result['output_path']).name}\n")
                
                if result.get("warnings"):
                    f.write(f"   Warnings:\n")
                    for warning in result["warnings"]:
                        f.write(f"     - {warning}\n")
            else:
                f.write(f"   Error: {result['error']}\n")
            
            f.write("\n")
        
        # Summary statistics
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful
        total_captions = sum(r["caption_count"] for r in results if r["status"] == "success")
        total_duration = sum(r["duration_sec"] for r in results if r["status"] == "success")
        
        f.write("=" * 60 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total files: {len(results)}\n")
        f.write(f"Successful: {successful}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Total captions generated: {total_captions}\n")
        f.write(f"Total audio duration: {total_duration:.1f}s\n")
    
    print(f"📋 Processing log written to: {log_path}")


def print_batch_summary(results: List[Dict]) -> None:
    """Print batch processing summary to console."""
    
    successful = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - successful
    total_captions = sum(r["caption_count"] for r in results if r["status"] == "success")
    total_duration = sum(r["duration_sec"] for r in results if r["status"] == "success")
    
    print("=" * 60)
    print("🎬 BATCH PROCESSING COMPLETE")
    print("=" * 60)
    print(f"📊 Files processed: {len(results)}")
    print(f"✅ Successful: {successful}")
    if failed > 0:
        print(f"❌ Failed: {failed}")
    print(f"📝 Total captions: {total_captions}")
    print(f"⏱️  Total duration: {total_duration:.1f}s")
    
    if failed > 0:
        print(f"\n❌ Failed files:")
        for result in results:
            if result["status"] == "failed":
                print(f"   {result['filename']}: {result['error']}")
    
    print("=" * 60)