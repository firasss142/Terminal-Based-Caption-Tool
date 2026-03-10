#!/usr/bin/env python3
"""SRT Caption Generator for CapCut - Main CLI entrypoint.

Tunisian Arabic forced alignment tool for generating CapCut-compatible SRT files.
"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from config import DEFAULT_LANGUAGE, MAX_CHARS_PER_LINE
from validator import validate_inputs
from normalize import normalize_audio
from aligner import align, align_word_level
from srt_writer import write_srt


def main():
    """Main CLI entrypoint for the SRT Caption Generator."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set up logging based on verbosity
    setup_logging(args.verbose)
    
    try:
        if args.batch:
            # Import batch module only when needed
            from batch import batch_process
            batch_process(args.input_dir, args.output_dir, args.language)
        else:
            # Single file processing
            process_single_file(args)
            
    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        if args.verbose:
            # Show full traceback in verbose mode
            raise
        else:
            # Show clean error message
            print(f"❌ Error: {e}")
            sys.exit(1)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="SRT Caption Generator for CapCut - Tunisian Arabic Forced Alignment Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --audio input/video.mp3 --script input/video.txt
  %(prog)s --audio input/video.wav --script input/script.txt --output custom.srt
  %(prog)s --audio input/video.m4a --script input/script.txt --offset -200
  %(prog)s --batch --input-dir input/ --output-dir output/
        """
    )
    
    # Single file mode arguments
    parser.add_argument(
        "--audio",
        type=str,
        help="Path to audio file (mp3, wav, m4a, aac)"
    )
    
    parser.add_argument(
        "--script", 
        type=str,
        help="Path to script text file (UTF-8)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output SRT file path (default: output/{audio_name}.srt)"
    )
    
    parser.add_argument(
        "--language",
        type=str,
        default=DEFAULT_LANGUAGE,
        help=f"Alignment language code (default: {DEFAULT_LANGUAGE})"
    )
    
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Global timestamp offset in milliseconds (positive or negative)"
    )
    
    parser.add_argument(
        "--max-chars",
        type=int,
        default=MAX_CHARS_PER_LINE,
        help=f"Auto-split long captions at word boundaries (default: {MAX_CHARS_PER_LINE})"
    )
    
    parser.add_argument(
        "--word-level",
        action="store_true",
        help="Use word-level alignment instead of sentence-level"
    )
    
    # Batch mode arguments
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all audio files in input directory"
    )
    
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Input directory for batch processing"
    )
    
    parser.add_argument(
        "--output-dir", 
        type=str,
        help="Output directory for batch processing"
    )
    
    # General options
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed alignment information and stack traces"
    )
    
    return parser


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)s - %(name)s - %(message)s'
        )
    else:
        logging.basicConfig(level=logging.WARNING)


def process_single_file(args: argparse.Namespace) -> None:
    """Process a single audio/script file pair."""
    
    # Validate required arguments for single file mode
    if not args.audio:
        raise ValueError("--audio is required for single file processing")
    if not args.script:
        raise ValueError("--script is required for single file processing")
    
    audio_path = Path(args.audio)
    script_path = Path(args.script)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_filename = audio_path.stem + ".srt"
        output_path = output_dir / output_filename
    
    print(f"🎬 Processing: {audio_path.name} + {script_path.name}")
    
    # Step 1: Validate inputs
    print("🔍 Validating inputs...")
    validation_result = validate_inputs(audio_path, script_path)
    
    # Print warnings if any
    for warning in validation_result["warnings"]:
        print(f"⚠️  {warning}")
    
    print(f"📊 Audio: {validation_result['audio_duration_sec']:.1f}s, "
          f"Script: {validation_result['sentence_count']} sentences, "
          f"{validation_result['word_count']} words")
    
    # Step 2: Normalize audio
    print("🔊 Normalizing audio...")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        temp_wav_path = tmp_file.name
    
    try:
        normalize_audio(audio_path, temp_wav_path)
        
        # Step 3: Load script
        print("📝 Loading script...")
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # Split into sentences and remove empty lines
        sentences = [line.strip() for line in script_content.splitlines() if line.strip()]
        
        if not sentences:
            raise ValueError(f"No non-empty lines found in script: {script_path}")
        
        print(f"📋 Found {len(sentences)} sentences for alignment")
        
        # Step 4: Perform alignment
        if args.word_level:
            print("🤖 Performing word-level forced alignment...")
            segments = align_word_level(temp_wav_path, sentences, args.language, args.max_chars)
        else:
            print("🤖 Performing sentence-level forced alignment...")
            segments = align(temp_wav_path, sentences, args.language)
            
            # Apply auto-split for long captions if needed
            if args.max_chars != MAX_CHARS_PER_LINE:
                segments = _split_long_captions(segments, args.max_chars)
        
        # Step 5: Apply timestamp offset if specified
        if args.offset != 0:
            print(f"⏰ Applying {args.offset}ms offset to all timestamps")
            for segment in segments:
                segment["start_ms"] = max(0, segment["start_ms"] + args.offset)
                segment["end_ms"] = max(segment["start_ms"] + 100, segment["end_ms"] + args.offset)
        
        # Step 6: Write SRT file
        print("💾 Writing SRT file...")
        write_srt(segments, output_path, apply_grouping=args.word_level)
        
        # Step 7: Print summary
        duration_sec = validation_result["audio_duration_sec"]
        print(f"🎬 Done. {len(segments)} captions | Duration: {duration_sec:.1f}s | Output: {output_path}")
        
        # Print per-segment details in verbose mode
        if args.verbose:
            print("\n📋 Alignment details:")
            for segment in segments:
                start_sec = segment["start_ms"] / 1000
                end_sec = segment["end_ms"] / 1000
                text_preview = segment["text"][:50] + ("..." if len(segment["text"]) > 50 else "")
                print(f"  {segment['index']:2d}: {start_sec:6.2f}-{end_sec:6.2f}s | {text_preview}")
        
    finally:
        # Clean up temporary WAV file
        try:
            Path(temp_wav_path).unlink()
        except OSError:
            pass  # File already deleted or doesn't exist


def _split_long_captions(segments: List[Dict], max_chars: int) -> List[Dict]:
    """Split captions that exceed max_chars at word boundaries."""
    
    new_segments = []
    
    for segment in segments:
        text = segment["text"]
        
        if len(text) <= max_chars:
            new_segments.append(segment)
            continue
            
        # Split long caption at word boundaries
        words = text.split()
        current_text = ""
        split_segments = []
        
        for word in words:
            # Check if adding this word would exceed limit
            test_text = f"{current_text} {word}".strip()
            
            if len(test_text) <= max_chars:
                current_text = test_text
            else:
                # Start new segment if we have text
                if current_text:
                    split_segments.append(current_text)
                current_text = word
        
        # Add remaining text
        if current_text:
            split_segments.append(current_text)
        
        # If splitting resulted in multiple segments, distribute time
        if len(split_segments) > 1:
            total_duration = segment["end_ms"] - segment["start_ms"]
            duration_per_split = total_duration // len(split_segments)
            
            for i, split_text in enumerate(split_segments):
                split_start = segment["start_ms"] + (i * duration_per_split)
                split_end = split_start + duration_per_split
                
                # Last segment gets any remaining time
                if i == len(split_segments) - 1:
                    split_end = segment["end_ms"]
                
                split_segment = {
                    "index": len(new_segments) + 1,
                    "text": split_text,
                    "start_ms": split_start,
                    "end_ms": split_end
                }
                new_segments.append(split_segment)
        else:
            # No splitting needed
            new_segments.append(segment)
    
    # Reindex all segments
    for i, segment in enumerate(new_segments):
        segment["index"] = i + 1
    
    return new_segments


if __name__ == "__main__":
    main()