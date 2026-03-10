# SRT Caption Generator for CapCut
## Tunisian Arabic Forced Alignment Tool

A local CLI tool for generating accurate SRT caption files from audio and script text, specifically designed for CapCut import compatibility and Tunisian Arabic dialect (Arabic + French code-switching).

---

## Features

✅ **Forced Alignment**: Precisely align existing scripts with audio (no transcription)  
✅ **CapCut Compatible**: UTF-8, CRLF line endings, perfect import every time  
✅ **Tunisian Arabic**: Handles Arabic + French code-switching seamlessly  
✅ **CPU Only**: Runs on MacBook without GPU requirements  
✅ **Batch Processing**: Process 20+ videos with one command  
✅ **Quality Features**: Word-level alignment, auto-split long captions, smart gap correction  

---

## Quick Start

### 1. Install Dependencies
```bash
# Install FFmpeg (required for audio processing)
brew install ffmpeg

# Install Python packages
pip install ctc-forced-aligner torch torchaudio
```

### 2. Basic Usage
```bash
# Single file processing
python3 align.py --audio input/video.mp3 --script input/script.txt

# Batch processing (auto-matches filenames)
python3 align.py --batch --input-dir input/ --output-dir output/

# Word-level alignment for precise timing
python3 align.py --audio input/video.wav --script input/script.txt --word-level
```

### 3. Test Installation
```bash
python3 test_basic.py
```

---

## Project Structure

```
caption-tool/
├── align.py              ← Main CLI entrypoint
├── normalize.py          ← Audio normalization 
├── aligner.py            ← Forced alignment core
├── srt_writer.py         ← SRT formatting + output
├── validator.py          ← Input validation
├── batch.py              ← Batch processing
├── config.py             ← Constants and defaults
├── input/                ← Drop audio + txt files here
├── output/               ← SRT files generated here
└── docs/                 ← Detailed documentation
    ├── CLI.md
    ├── ALIGNER.md
    ├── TROUBLESHOOTING.md
    └── ...
```

---

## Usage Examples

### Single File Processing
```bash
# Basic alignment
python3 align.py --audio input/video_01.mp3 --script input/video_01.txt

# Custom output path
python3 align.py --audio input/video.wav --script input/script.txt --output custom.srt

# Adjust timing (shift captions earlier)
python3 align.py --audio input/video.m4a --script input/script.txt --offset -200
```

### Quality Options
```bash
# Word-level alignment (more precise for fast speech)
python3 align.py --audio input/video.wav --script input/script.txt --word-level

# Custom caption length limit
python3 align.py --audio input/video.mp3 --script input/script.txt --max-chars 30

# Verbose output for debugging
python3 align.py --audio input/video.wav --script input/script.txt --verbose
```

### Batch Processing
```bash
# Process all matched pairs in directory
python3 align.py --batch --input-dir input/ --output-dir output/

# Input structure:
# input/
# ├── video_01.mp3 ↔ video_01.txt
# ├── video_02.wav ↔ video_02.txt
# └── video_03.m4a ↔ video_03.txt
```

---

## Expected Workflow

1. **Record voiceover** from your written script
2. **Export audio** as MP3/WAV from your video editor
3. **Save script** as UTF-8 text file with same filename
4. **Run alignment**: `python3 align.py --audio video.mp3 --script video.txt`
5. **Import SRT** directly into CapCut - captions appear accurately timed

**No manual timestamping. No CapCut caption editing. Just perfect alignment.**

---

## Supported Formats

- **Audio**: MP3, WAV, M4A, AAC
- **Text**: UTF-8 encoded plain text
- **Output**: CapCut-compatible SRT files

---

## Quality Features

- **Smart Gap Correction**: Automatically fixes overlapping captions
- **Character Limits**: Auto-split long captions at word boundaries  
- **Word-Level Mode**: More precise timing for fast-speaking segments
- **Confidence Warnings**: Alerts for low-quality alignments
- **Validation Checks**: Prevents common audio/script mismatches

---

## Documentation

- **[CLI.md](docs/CLI.md)**: Complete command-line reference
- **[ALIGNER.md](docs/ALIGNER.md)**: Alignment engine details
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**: Common issues and fixes
- **[SRT_WRITER.md](docs/SRT_WRITER.md)**: SRT formatting specifics
- **[BATCH.md](docs/BATCH.md)**: Batch processing guide

---

## Troubleshooting

### First Run
- Model download (~1GB) happens automatically on first use
- Requires stable internet connection and ~2GB free disk space

### Common Issues
- **Arabic text garbled**: Ensure script file is UTF-8 encoded
- **Captions too early/late**: Use `--offset` flag to adjust timing
- **Low alignment confidence**: Try `--word-level` mode for better precision
- **Import fails in CapCut**: Generated SRT uses correct formatting automatically

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions.

---

## Technical Details

- **Alignment Model**: facebook/mms-300m (HuggingFace)
- **Alignment Library**: ctc-forced-aligner
- **Audio Processing**: FFmpeg normalization to 16kHz mono WAV
- **Language Support**: Arabic (ara) + multilingual text
- **Platform**: macOS (CPU-only, no CUDA required)
- **Line Endings**: CRLF for CapCut compatibility

---

## License

This tool is designed specifically for content creators producing Tunisian Arabic videos. Use responsibly and ensure you have rights to the audio content you're processing.

---

## Contributing

This is a specialized tool built to exact specifications. For issues or feature requests related to CapCut compatibility or Tunisian Arabic handling, please document them with specific test cases.