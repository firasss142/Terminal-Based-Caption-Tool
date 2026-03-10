# CLI
> Last updated: 2026-03-09

## Purpose
Main command-line interface for the SRT Caption Generator. Provides single-file and batch processing modes with comprehensive error handling and progress reporting for Tunisian Arabic content creators.

## Function Signature
```python
def main() -> None:
```

## Parameters
Command-line arguments (via argparse):

| Argument | Type | Required | Default | Description |
|---|---|---|---|---|
| --audio | str | Yes (single) | - | Path to audio file (mp3, wav, m4a, aac) |
| --script | str | Yes (single) | - | Path to script text file (UTF-8) |
| --output | str | No | output/{audio_name}.srt | Custom output SRT file path |
| --language | str | No | "ara" | Alignment language code |
| --offset | int | No | 0 | Global timestamp offset in milliseconds |
| --max-chars | int | No | 42 | Auto-split long captions at word boundaries |
| --word-level | flag | No | False | Use word-level alignment instead of sentence-level |
| --batch | flag | No | False | Enable batch processing mode |
| --input-dir | str | Yes (batch) | - | Input directory for batch processing |
| --output-dir | str | Yes (batch) | - | Output directory for batch processing |
| --verbose | flag | No | False | Print detailed alignment information |

## Returns
Exit code 0 on success, 1 on error.

## Error Handling
| Condition | Behavior |
|---|---|
| Missing required arguments | Clean error message, exit code 1 |
| File not found | Descriptive error with file path |
| Alignment failure | Model download hints or alignment error details |
| Keyboard interrupt | Clean "Process interrupted" message |
| Unexpected errors | Stack trace in --verbose mode, clean message otherwise |

## Usage Example
```bash
# Basic single file processing
python3 align.py --audio input/video_01.mp3 --script input/video_01.txt

# Custom output path and offset
python3 align.py --audio input/video.wav --script input/script.txt --output custom.srt --offset -200

# Verbose output with debugging
python3 align.py --audio input/video.m4a --script input/script.txt --verbose

# Word-level alignment with custom character limit
python3 align.py --audio input/video.wav --script input/script.txt --word-level --max-chars 30

# Auto-split long captions without word-level alignment
python3 align.py --audio input/video.mp3 --script input/script.txt --max-chars 25

# Batch processing
python3 align.py --batch --input-dir input/ --output-dir output/
```

## Known Edge Cases
- **First run model download**: Shows "📥 Downloading alignment model..." message, may take several minutes
- **Missing ffmpeg**: Clear installation instructions provided in error message
- **Corrupted files**: Validation catches issues early with descriptive messages
- **Timestamp offset edge cases**: Prevents negative timestamps, maintains minimum caption duration
- **Memory constraints**: Large files processed efficiently via streaming alignment
- **Mixed file encodings**: UTF-8 validation prevents garbled Arabic text processing
- **Keyboard interruption**: Graceful cleanup of temporary files

## Dependencies
- **Python 3.10+**: Required for Union type hints and pathlib features
- **ctc-forced-aligner**: Core alignment library
- **torch + torchaudio**: PyTorch ecosystem for model inference
- **ffmpeg**: System dependency for audio processing
- All local modules: validator, normalize, aligner, srt_writer, config