# VALIDATOR
> Last updated: 2026-03-09

## Purpose
Performs comprehensive pre-flight validation of audio and script files before forced alignment processing. Ensures files exist, are properly formatted, and have realistic word count to duration ratios for Tunisian Arabic content.

## Function Signature
```python
def validate_inputs(audio_path: Union[str, Path], script_path: Union[str, Path]) -> Dict:
```

## Parameters
| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| audio_path | Union[str, Path] | Yes | - | Path to audio file for validation |
| script_path | Union[str, Path] | Yes | - | Path to script text file for validation |

## Returns
Dictionary with validation results and warnings:
```python
{
    "audio_duration_sec": 23.5,
    "sentence_count": 4,
    "word_count": 58,
    "warnings": ["Script may be too short for audio duration..."]
}
```

## Error Handling
| Exception | Condition |
|---|---|
| FileNotFoundError | Audio or script file doesn't exist |
| ValueError | File is empty, script not UTF-8, or no valid content |
| RuntimeError | ffprobe fails or can't analyze audio duration |

## Usage Example
```python
from validator import validate_inputs

result = validate_inputs("input/video.mp3", "input/video.txt")
print(f"Duration: {result['audio_duration_sec']}s")
print(f"Sentences: {result['sentence_count']}")
for warning in result['warnings']:
    print(f"⚠️ {warning}")
```

## Known Edge Cases
- **Mixed Arabic/French script**: Word counting handles code-switching by splitting on whitespace
- **Empty lines in script**: Automatically filtered out, only non-empty lines count as sentences  
- **Special characters**: Preserved as-is, no normalization or filtering applied
- **Very short audio**: Duration validation may trigger false positives for audio < 5 seconds
- **Corrupted audio**: ffprobe will fail with descriptive error message
- **Non-UTF8 script**: Explicit check prevents garbled Arabic text processing

## Dependencies
- **ffprobe** (part of ffmpeg): System requirement for audio duration analysis
- **pathlib**: Built-in Python module
- **subprocess**: Built-in Python module
- **re**: Built-in Python module for text processing