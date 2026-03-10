# ALIGNER
> Last updated: 2026-03-10

## Purpose
Performs forced alignment between audio and text using the ctc-forced-aligner library.

Two modes are available:
- **Sentence-level** (`align`): uses `AlignmentTorchSingleton` + torchaudio MMS_FA pipeline.  Best for Latin/French-only scripts.
- **Word-level** (`align_word_level`): uses `AlignmentSingleton` (ONNX) + uroman romanisation.  Required for Arabic or mixed Arabic/French scripts.  Returns one dict per original script word.

## Why ONNX for Arabic

The MMS_FA torchaudio pipeline dictionary contains only 28 Latin phoneme characters.  Arabic characters are stripped before CTC alignment — so the torch path cannot produce word timestamps for Arabic text.

The ONNX path uses `unidecode` / uroman to romanise every word (Arabic, French, numbers) into the same phoneme space before alignment.  The original text is preserved in the output via `text_starred` — Arabic and French words come back unchanged.

### Verified API call chain (word-level)
```python
from ctc_forced_aligner import (
    AlignmentSingleton, load_audio, generate_emissions,
    preprocess_text, get_alignments, get_spans, postprocess_results,
)

audio   = load_audio(wav_path)                           # numpy float32, mono 16kHz
aligner = AlignmentSingleton()                           # loads ~1.3 GB ONNX model once

emissions, stride = generate_emissions(aligner.model, audio, batch_size=4)
tokens_starred, text_starred = preprocess_text(
    full_text, romanize=True, language="ara", split_size="word"
)
# text_starred = ["<star>","كنت","<star>","ماشي","<star>","cellulite",...]
segments, scores, blank_token = get_alignments(emissions, tokens_starred, aligner.tokenizer)
spans      = get_spans(tokens_starred, segments, blank_token)
word_timestamps = postprocess_results(text_starred, spans, stride, scores)
# word_timestamps = [{"start":0.0,"end":0.3,"text":"كنت","score":...}, ...]
```

`postprocess_results` skips `<star>` tokens automatically.  `text` field contains the **original** script word (Arabic, French, digits).

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
    """Sentence-level: returns one dict per input sentence line."""

def align_word_level(audio_path, sentences, language="ara", max_chars=42) -> List[Dict]:
    """Word-level: returns one dict per whitespace-split script word.
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
- ONNX model: ~1.3 GB, cached at `~/ctc_forced_aligner/model.onnx`
- Downloaded automatically on first run via `ensure_onnx_model()`
- Use `curl -L -C - --retry 10 ...` if the Python downloader times out

## Word Count Guarantee
`split_text("word")` uses `str.split()` — same tokeniser as the script loader.
Word count in `word_timestamps` equals `len(full_text.split())` when all words
romanise to at least one phoneme token (true for Arabic and standard French).

## Known Edge Cases
- **Arabic-only lines**: fully handled by uroman romanisation
- **Mixed Arabic/French**: both word types get individual timestamps
- **French accents** (é, è, à): unidecode strips to base ASCII before alignment; original word text is preserved from `text_starred`
- **Digits / "100%"**: "%" strips to empty; digit survives — word count may shift by 1
- **Smart gap correction**: runs after alignment to fix any overlaps (50 ms gap)
- **Minimum caption duration**: 100 ms enforced during `group_words()` timing pass
