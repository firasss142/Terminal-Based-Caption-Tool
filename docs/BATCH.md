# BATCH
> Last updated: 2026-03-09

## Purpose
Processes multiple audio/script file pairs in batch mode, automatically matching files by filename stem and generating comprehensive processing logs. Designed for content teams processing 20+ videos weekly.

## Function Signature
```python
def batch_process(input_dir: Union[str, Path], output_dir: Union[str, Path], language: str = "ara") -> None:
```

## Parameters
| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| input_dir | Union[str, Path] | Yes | - | Directory containing audio and script files |
| output_dir | Union[str, Path] | Yes | - | Directory where SRT files will be written |
| language | str | No | "ara" | Alignment language code for all files |

## Returns
None - Prints progress and generates processing_log.txt in output directory.

## Error Handling
| Exception | Condition |
|---|---|
| ValueError | Input directory doesn't exist or no pairs found |
| Individual file errors | Logged and reported, don't stop batch processing |

## Usage Example
```bash
# CLI usage
python3 align.py --batch --input-dir input/ --output-dir output/

# Programmatic usage
from batch import batch_process
batch_process("input/", "output/", language="ara")
```

Input directory structure:
```
input/
├── video_01.mp3
├── video_01.txt
├── video_02.wav  
├── video_02.txt
├── podcast_intro.m4a
├── podcast_intro.txt
└── unmatched.mp3  # Will be skipped with warning
```

Output:
```
output/
├── video_01.srt
├── video_02.srt
├── podcast_intro.srt
└── processing_log.txt
```

## Known Edge Cases
- **Filename matching**: Only exact stem matches work (video_01.mp3 ↔ video_01.txt)
- **Mixed file extensions**: Supports mp3, wav, m4a, aac automatically
- **Processing failures**: Individual failures don't stop batch, all logged in detail
- **Large batches**: Memory efficient - processes one file at a time
- **Duplicate names**: Last processed file wins, earlier ones overwritten
- **Empty directories**: Graceful handling with clear "no pairs found" message
- **Permission issues**: Detailed error reporting per file

## Dependencies
- **datetime**: Built-in Python module for timestamps
- **pathlib**: Built-in Python module for file operations
- **tempfile**: Built-in Python module for temporary file handling
- All alignment modules: validator, normalize, aligner, srt_writer