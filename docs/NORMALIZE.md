# NORMALIZE
> Last updated: 2026-03-09

## Purpose
Converts audio files from various formats (mp3, wav, m4a, aac) to the specific format required by the facebook/mms-300m forced alignment model: mono, 16kHz, 16-bit PCM WAV.

## Function Signature
```python
def normalize_audio(input_path: Union[str, Path], output_path: Union[str, Path]) -> str:
```

## Parameters
| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| input_path | Union[str, Path] | Yes | - | Path to input audio file (mp3, wav, m4a, aac) |
| output_path | Union[str, Path] | Yes | - | Path for normalized WAV output |

## Returns
String path to the normalized WAV file on successful conversion.

Example: `"/tmp/normalized_audio.wav"`

## Error Handling
| Exception | Condition |
|---|---|
| FileNotFoundError | Input file doesn't exist or is empty |
| RuntimeError | ffmpeg conversion fails, ffmpeg not installed, or output file not created |

## Usage Example
```python
from normalize import normalize_audio

# Convert MP3 to normalized WAV
output_path = normalize_audio("input/video.mp3", "/tmp/video_normalized.wav")
# Output: "✅ Audio normalized → /tmp/video_normalized.wav"
```

## Known Edge Cases
- **Large files**: ffmpeg handles large files efficiently, no special handling needed
- **Corrupted audio**: ffmpeg will fail with descriptive error message
- **Unsupported formats**: ffmpeg supports 100+ formats, very rare to encounter unsupported format
- **Permission errors**: Output directory is created automatically with proper permissions
- **Disk space**: No validation for available disk space (user responsibility)

## Dependencies
- **ffmpeg**: System requirement, must be installed via `brew install ffmpeg` on macOS
- **pathlib**: Built-in Python module
- **subprocess**: Built-in Python module