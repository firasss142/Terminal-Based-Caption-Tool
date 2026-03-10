# Shared constants and defaults for the SRT Caption Generator
# Do not modify these values unless you understand the implications for CapCut compatibility

# Audio processing settings
SAMPLE_RATE = 16000
MODEL_ID = "facebook/mms-300m"
DEFAULT_LANGUAGE = "ara"

# SRT file format settings - critical for CapCut compatibility
SRT_ENCODING = "utf-8"
SRT_LINE_ENDING = "\r\n"  # CRLF required by CapCut

# Caption display optimization
MAX_CHARS_PER_LINE = 42   # Optimal for mobile viewing
GAP_BETWEEN_CAPTIONS_MS = 50  # 50ms gap prevents subtitle flash

# Validation thresholds
MIN_WORDS_PER_MINUTE = 80   # Conservative lower bound for Tunisian Arabic
MAX_WORDS_PER_MINUTE = 180  # Upper bound for fast speech
MISMATCH_THRESHOLD = 0.4    # 40% mismatch triggers warning

# Alignment quality settings
MIN_CONFIDENCE = 0.4        # Minimum confidence for alignment segments
MIN_CAPTION_DURATION_MS = 100  # Minimum duration per caption
MAX_GAP_WARNING_MS = 500    # Warn if gap between captions exceeds this

# Performance optimization settings
MODEL_CACHE_DIR = ".model_cache"  # Local model cache directory
MAX_AUDIO_LENGTH_SEC = 600   # Maximum audio length for processing (10 minutes)
TEMP_FILE_PREFIX = "caption_tool_"  # Prefix for temp files
CONCURRENT_BATCH_SIZE = 4    # Number of files to process concurrently in batch mode

# Word-level alignment settings - OPTIMIZED FOR TUNISIAN ARABIC
ALIGNMENT_GRANULARITY = "word"   # "word" or "sentence" - word recommended
MAX_TOKENS_PER_CAPTION = 3       # Maximum grouped tokens per caption block
DEFAULT_WORD_LEVEL = True        # Enable word-level by default for optimal granularity

# Arabic particles that drive grouping logic in srt_writer.group_words()
ARABIC_PARTICLES = {
    "في", "من", "و", "ولا", "كان", "على", "مع", "باش",
    "هو", "هي", "اللي", "لي", "تحت", "فوق", "ال", "لا",
    "ما", "وما", "كيما", "لين", "وقتلي", "واللي",
}