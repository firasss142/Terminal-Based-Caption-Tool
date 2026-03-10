# CONFIG
> Last updated: 2026-03-10

## Purpose
Defines all shared constants and default values used across the SRT Caption Generator modules. These values are carefully tuned for CapCut compatibility and Tunisian Arabic dialect processing.

## Function Signature
```python
# Constants only - no functions in this module
```

## Parameters
| Constant | Type | Value | Description |
|---|---|---|---|
| SAMPLE_RATE | int | 16000 | Audio sample rate for forced alignment model |
| MODEL_ID | str | "facebook/mms-300m" | HuggingFace model identifier |
| DEFAULT_LANGUAGE | str | "ara" | ISO language code for Arabic |
| SRT_ENCODING | str | "utf-8" | File encoding for SRT output |
| SRT_LINE_ENDING | str | "\r\n" | CRLF line endings required by CapCut |
| MAX_CHARS_PER_LINE | int | 42 | Optimal character count for mobile viewing |
| GAP_BETWEEN_CAPTIONS_MS | int | 50 | Minimum gap between captions to prevent flash |
| MIN_WORDS_PER_MINUTE | int | 80 | Lower bound for speech rate validation |
| MAX_WORDS_PER_MINUTE | int | 180 | Upper bound for speech rate validation |
| MISMATCH_THRESHOLD | float | 0.4 | Threshold for duration/word count mismatch warning |
| MIN_CONFIDENCE | float | 0.4 | Minimum alignment confidence threshold |
| MIN_CAPTION_DURATION_MS | int | 100 | Minimum duration for any caption |
| MAX_GAP_WARNING_MS | int | 500 | Gap threshold that triggers warning |
| ALIGNMENT_GRANULARITY | str | "word" | Default granularity: "word" or "sentence" |
| MAX_TOKENS_PER_CAPTION | int | 3 | Maximum grouped tokens per caption block |
| ARABIC_PARTICLES | set | (see below) | Arabic function words that drive grouping logic in `group_words()` |

### ARABIC_PARTICLES
```python
ARABIC_PARTICLES = {
    "في", "من", "و", "ولا", "كان", "على", "مع", "باش",
    "هو", "هي", "اللي", "لي", "تحت", "فوق", "ال", "لا",
    "ما", "وما", "كيما", "لين", "وقتلي", "واللي",
}
```
Used by `srt_writer.group_words()` to decide whether a third token in a potential 3-token block is a content word or another particle.

## Returns
N/A - This module only exports constants.

## Error Handling
No error handling - constants only.

## Usage Example
```python
from config import SAMPLE_RATE, SRT_LINE_ENDING, MAX_CHARS_PER_LINE, ARABIC_PARTICLES
```

## Known Edge Cases
N/A - No logic in this module.

## Dependencies
None - pure Python constants.
