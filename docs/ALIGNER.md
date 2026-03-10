# ALIGNER
> Last updated: 2026-03-10

## Purpose
Performs forced alignment between audio and text using the ctc-forced-aligner library.

Two modes are available:
- **Sentence-level** (`align`): uses `AlignmentTorchSingleton` + `aligner.generate_srt()` with `model_type='MMS_FA'`.  Best for Latin/French-only scripts.
- **Word-level** (`align_word_level`): uses `torchaudio.pipelines.MMS_FA` (PyTorch, NOT ONNX) + `unidecode` romanisation.  Required for Arabic or mixed Arabic/French scripts.  Returns one dict per original script word.

## Why unidecode romanisation for Arabic

The MMS_FA torchaudio pipeline dictionary contains only 28 Latin phoneme characters.  Arabic characters are not in the dictionary — so Arabic words cannot be aligned directly.

`unidecode` transliterates every word (Arabic, French, numbers) into ASCII before alignment.  The original text is preserved in the output via positional mapping (`pos_map`) — Arabic and French words come back unchanged.

### Actual API call chain (word-level)
```python
import torch
import torchaudio
import torchaudio.functional as F
from unidecode import unidecode
from ctc_forced_aligner import (
    load_audio as cfa_load_audio,
    align as cfa_align,
    unflatten,
    _postprocess_results,
)

device = torch.device("cpu")
bundle = torchaudio.pipelines.MMS_FA
dictionary = bundle.get_dict(star=None)
model = bundle.get_model(with_star=False).to(device)

waveform = cfa_load_audio(wav_path, ret_type="torch").to(device)

with torch.inference_mode():
    emission, _ = model(waveform)

# Romanise each word with unidecode, filter to MMS_FA phoneme set
romanized = [unidecode(w).lower() for w in original_words]
cleaned = [
    "".join(c for c in rom if c in dictionary and dictionary[c] != 0)
    for rom in romanized
]

# Build transcript list and positional map (skipping empty-romanised words)
transcript = [cw for cw in cleaned if cw]
pos_map = [i for i, cw in enumerate(cleaned) if cw]

tokenized = [dictionary[c] for word in transcript for c in word
             if c in dictionary and dictionary[c] != 0]
aligned_tokens, alignment_scores = cfa_align(emission, tokenized, device)
token_spans = F.merge_tokens(aligned_tokens[0], alignment_scores[0])
word_spans = unflatten(token_spans, [len(w) for w in transcript])
word_ts = _postprocess_results(
    transcript, word_spans, waveform,
    emission.size(1), bundle.sample_rate, alignment_scores
)
# word_ts[i]: {"start": sec, "end": sec, "text": cleaned_word}

# Map timestamps back to original words via pos_map
ts_by_orig = {pos_map[i]: word_ts[i] for i in range(len(pos_map))}
```

`text` field in the output is the **original** script word (Arabic, French, digits), recovered via `pos_map`.

### Example word-level output (first 5 words of biovera script)
```
index  start_ms  end_ms   text
  1         0     300    كنت
  2       300     600    ماشي
  3       600     700    في
  4       700    1000    بالي
  5      1000    1166    اللي
```

## Function Signatures
```python
def align(audio_path, sentences, language="ara") -> List[Dict]:
    """Sentence-level: returns one dict per input sentence line.
    Uses AlignmentTorchSingleton.generate_srt() with model_type='MMS_FA'."""

def align_word_level(audio_path, sentences, language="ara", max_chars=42) -> List[Dict]:
    """Word-level: returns one dict per whitespace-split script word.
    Uses torchaudio.pipelines.MMS_FA + unidecode romanisation.
    Grouping into caption blocks is handled by srt_writer.group_words()."""
```

## Output Format
```python
[
    {"index": 1, "text": "كنت",       "start_ms": 0,   "end_ms": 300},
    {"index": 2, "text": "ماشي",      "start_ms": 300, "end_ms": 600},
    {"index": 3, "text": "cellulite", "start_ms": 1633,"end_ms": 2133},
    ...
]
```

## Model Download
- MMS_FA PyTorch model: ~1.2 GB, cached at `~/.cache/torch/hub/checkpoints/`
- Downloaded automatically via `torchaudio.pipelines.MMS_FA` on first run
- ONNX model (`~/ctc_forced_aligner/model.onnx`) is NOT used by any current code path

## Word Count Guarantee
Words are split with `str.split()` — same tokeniser as the script loader.
Words that romanise to empty string (e.g. "100%") are interpolated: placed
immediately after the previous word with `MIN_CAPTION_DURATION_MS` duration.

## Known Edge Cases
- **Arabic-only lines**: fully handled by unidecode romanisation
- **Mixed Arabic/French**: both word types get individual timestamps
- **French accents** (é, è, à): unidecode strips to base ASCII before alignment; original word text is preserved via pos_map
- **Digits / "100%"**: "%" strips to empty; digit survives — handled by interpolation fallback
- **Smart gap correction**: runs after alignment in `_apply_smart_gap_correction()` to fix any overlaps (50 ms gap)
- **Minimum caption duration**: 100 ms enforced during `group_words()` → `_enforce_timing()` pass
