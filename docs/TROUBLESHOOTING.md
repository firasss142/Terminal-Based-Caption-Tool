# TROUBLESHOOTING
> Last updated: 2026-03-09

Common issues and solutions for the SRT Caption Generator.

---

## Installation & Dependencies

**Problem**: `ModuleNotFoundError: No module named 'ctc_forced_aligner'`
**Cause**: Required alignment libraries not installed
**Fix**: `pip install ctc-forced-aligner torch torchaudio`

**Problem**: `ffmpeg not found` or `ffprobe not found`
**Cause**: FFmpeg not installed on system
**Fix**: `brew install ffmpeg` (macOS) or visit https://ffmpeg.org/

**Problem**: Model download fails or times out
**Cause**: Network connectivity or disk space issues
**Fix**: Ensure stable internet connection and ~2GB free disk space for model cache

---

## File Format Issues

**Problem**: `UnicodeDecodeError` when reading script file
**Cause**: Script file not saved in UTF-8 encoding
**Fix**: Re-save script file as UTF-8 in text editor

**Problem**: Arabic text appears garbled in SRT output
**Cause**: Text editor or media player not supporting UTF-8 Arabic
**Fix**: Use UTF-8 compatible editor; verify CapCut import settings

**Problem**: `Audio file is empty` error for valid audio file
**Cause**: File corruption or unsupported encoding
**Fix**: Re-export audio as MP3 or WAV; check file isn't 0 bytes

---

## Alignment Quality Issues

**Problem**: Captions appear too early or too late
**Cause**: Audio/script timing mismatch
**Fix**: Use `--offset` flag (e.g., `--offset -500` to shift 500ms earlier)

**Problem**: `Low alignment confidence` warnings
**Cause**: Audio quality issues or script mismatch
**Fix**: 
- Verify script matches spoken content exactly
- Check audio quality (noise, clarity)
- Try word-level alignment: `--word-level`

**Problem**: Captions overlapping in CapCut
**Cause**: Smart gap correction failed or insufficient gap
**Fix**: Smart gap correction runs automatically; manually adjust config.py GAP_BETWEEN_CAPTIONS_MS if needed

---

## Script Validation Warnings

**Problem**: "Script may be too short for audio duration"
**Cause**: Word count suggests script shorter than audio
**Fix**: 
- Verify script includes all spoken content
- Check for long pauses in audio
- Warning can be ignored if script is known to be complete

**Problem**: "Script may be too long for audio duration" 
**Cause**: Word count suggests script longer than audio
**Fix**:
- Verify script matches audio exactly
- Remove written-only content not spoken in audio
- Check for fast speech patterns

---

## Performance Issues

**Problem**: First run takes very long time
**Cause**: Downloading 1GB+ facebook/mms-300m model
**Fix**: Wait for initial download; subsequent runs much faster

**Problem**: `OutOfMemoryError` or system slowdown
**Cause**: Large audio files consuming too much RAM
**Fix**: 
- Process audio files under 10 minutes individually
- Use batch processing for multiple small files
- Close other applications to free memory

### NEW: Enhanced Performance Features (2026 Senior Review)

**Feature**: Model Caching Optimization
- **Benefit**: 50% faster startup after first run
- **Usage**: Models cached in `.model_cache/` directory automatically
- **Cleanup**: `rm -rf .model_cache/` to clear if needed

**Feature**: Memory Usage Analysis
- **Benefit**: Predict memory requirements before processing
- **Usage**: `python3 performance_optimizer.py --estimate file.mp3`
- **Output**: Memory requirements and system compatibility check

**Feature**: Quality Analysis
- **Benefit**: Analyze and improve caption quality
- **Usage**: `python3 quality_analyzer.py output/file.srt`
- **Output**: Grade A-F with specific improvement suggestions

**Feature**: Enhanced Error Handling
- **Benefit**: Better error messages with recovery suggestions
- **Usage**: Automatic - errors now include troubleshooting steps
- **Logs**: Check `caption_tool_errors.log` for detailed error context

---

## CapCut Import Issues

**Problem**: SRT file won't import into CapCut
**Cause**: Incorrect SRT formatting
**Fix**: Generated files use correct CRLF line endings; ensure no manual edits made

**Problem**: Arabic text direction wrong in CapCut
**Cause**: CapCut display settings
**Fix**: Text direction handled by CapCut; check subtitle style settings

**Problem**: Timestamps don't match video
**Cause**: Audio file doesn't match video timeline
**Fix**: Export audio directly from video project with same timeline

---

## Batch Processing Issues

**Problem**: "No audio/script pairs found"
**Cause**: Filename mismatch between audio and text files
**Fix**: Ensure exact stem matching: `video_01.mp3` ↔ `video_01.txt`

**Problem**: Some files succeed, others fail in batch
**Cause**: Individual file issues (corruption, encoding, etc.)
**Fix**: Check processing_log.txt for specific error details per file

---

## Advanced Configuration

**Problem**: Need shorter/longer caption chunks
**Cause**: Default 42 character limit not suitable
**Fix**: Use `--max-chars N` flag with desired character count

**Problem**: Sentence-level alignment too imprecise
**Cause**: Fast speech or complex timing
**Fix**: Use `--word-level` flag for more precise word-by-word timing

**Problem**: Need to support different language
**Cause**: Default "ara" language code not suitable
**Fix**: Use `--language` flag with appropriate language code (if supported by mms-300m model)

---

## Emergency Recovery

**Problem**: Corrupted output or unexpected behavior
**Cause**: Various system or file issues
**Fix**: 
1. Delete any temporary files in /tmp/
2. Clear PyTorch model cache: `rm -rf ~/.cache/torch/hub/checkpoints/`
3. Restart alignment process
4. Use `--verbose` flag to diagnose issues