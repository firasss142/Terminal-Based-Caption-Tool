# SRT_WRITER
> Last updated: 2026-03-09

## Purpose
Converts aligned segments to properly formatted SRT subtitle files with strict CapCut compatibility requirements, including CRLF line endings, UTF-8 encoding without BOM, and precise timestamp formatting.

## Function Signature
```python
def write_srt(segments: List[Dict], output_path: Union[str, Path]) -> str:
```

## Parameters
| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| segments | List[Dict] | Yes | - | List of aligned segments from aligner module |
| output_path | Union[str, Path] | Yes | - | Path where SRT file should be written |

## Returns
String path to the written SRT file on successful generation.

Example: `"/Users/user/caption-tool/output/video.srt"`

## Error Handling
| Exception | Condition |
|---|---|
| ValueError | No segments provided, missing required fields, or invalid segment data |
| RuntimeError | File write permission errors or disk space issues |

## Usage Example
```python
from srt_writer import write_srt

segments = [
    {
        "index": 1,
        "text": "هذا المنتج غير عادي",
        "start_ms": 0,
        "end_ms": 2450
    }
]

output_path = write_srt(segments, "output/video.srt")
# Output: "✅ SRT written → output/video.srt (1 captions)"
```

Generated SRT format:
```
1
00:00:00,000 --> 00:00:02,450
هذا المنتج غير عادي

```

## Known Edge Cases
- **Arabic text direction**: Text preserved as-is, no RTL reordering applied (CapCut handles display)
- **Long captions**: No automatic text wrapping (handled by quality improvement features)
- **Special characters**: All Unicode characters preserved in UTF-8 encoding
- **Timestamp precision**: Millisecond precision maintained throughout conversion
- **Sequential indexing**: Indexes must be sequential starting from 1, gaps will cause CapCut import issues
- **Line ending consistency**: Strict CRLF (\r\n) enforcement for cross-platform compatibility
- **Empty segments**: Validation prevents empty text from generating invalid SRT blocks

## Dependencies
- **pathlib**: Built-in Python module for file path handling
- **config**: Local module for SRT formatting constants