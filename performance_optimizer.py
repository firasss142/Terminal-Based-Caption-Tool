"""Performance optimization utilities for the caption generation tool."""

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union
from contextlib import contextmanager

from config import MODEL_CACHE_DIR, MAX_AUDIO_LENGTH_SEC, TEMP_FILE_PREFIX

logger = logging.getLogger(__name__)


class ModelCacheManager:
    """Manages local model caching to avoid repeated downloads."""
    
    def __init__(self, cache_dir: str = MODEL_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
    def get_model_path(self, model_id: str) -> Optional[Path]:
        """Check if model is cached locally."""
        model_hash = hashlib.md5(model_id.encode()).hexdigest()[:8]
        model_path = self.cache_dir / f"model_{model_hash}"
        return model_path if model_path.exists() else None
    
    def cache_model(self, model_id: str, model_data: bytes) -> Path:
        """Cache model data locally."""
        model_hash = hashlib.md5(model_id.encode()).hexdigest()[:8] 
        model_path = self.cache_dir / f"model_{model_hash}"
        
        with open(model_path, 'wb') as f:
            f.write(model_data)
        
        logger.info(f"Cached model {model_id} to {model_path}")
        return model_path


class AudioValidator:
    """Enhanced audio validation with performance checks."""
    
    @staticmethod
    def validate_audio_duration(audio_path: Union[str, Path]) -> float:
        """Validate audio duration is within processing limits."""
        import subprocess
        
        audio_path = Path(audio_path)
        
        # Use ffprobe to get duration quickly without loading audio
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 
            'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            duration = float(result.stdout.strip())
            
            if duration > MAX_AUDIO_LENGTH_SEC:
                raise ValueError(
                    f"Audio too long: {duration:.1f}s (max: {MAX_AUDIO_LENGTH_SEC}s). "
                    "Consider splitting into smaller segments."
                )
            
            return duration
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError) as e:
            raise RuntimeError(f"Failed to validate audio duration: {e}")


@contextmanager
def temp_file_manager(suffix: str = ".tmp", prefix: str = TEMP_FILE_PREFIX):
    """Context manager for safe temporary file handling."""
    import tempfile
    
    temp_files = []
    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix, prefix=prefix, delete=False
        ) as f:
            temp_files.append(f.name)
            yield f.name
    finally:
        # Clean up all temp files
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink()
            except OSError:
                logger.warning(f"Failed to clean up temp file: {temp_file}")


class MemoryOptimizer:
    """Memory usage optimization utilities."""
    
    @staticmethod
    def estimate_memory_usage(audio_duration: float, word_count: int) -> Dict[str, float]:
        """Estimate memory requirements for processing."""
        # Rough estimates based on typical usage patterns
        audio_mb = audio_duration * 0.5  # ~500KB per second for 16kHz mono
        model_mb = 1200  # facebook/mms-300m model size
        alignment_mb = word_count * 0.01  # Alignment metadata
        
        total_mb = audio_mb + model_mb + alignment_mb
        
        return {
            "audio_mb": audio_mb,
            "model_mb": model_mb,
            "alignment_mb": alignment_mb,
            "total_mb": total_mb,
            "recommended_ram_gb": max(4.0, total_mb / 1024 * 1.5)
        }
    
    @staticmethod
    def check_available_memory() -> float:
        """Check available system memory in GB."""
        import psutil
        memory = psutil.virtual_memory()
        return memory.available / (1024**3)


class BatchProcessor:
    """Optimized batch processing with concurrency control."""
    
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        
    def process_batch_optimized(self, audio_script_pairs: List[tuple], 
                              output_dir: Path) -> List[Dict]:
        """Process multiple files with optimal resource usage."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        
        # Sort by file size for better load balancing
        pairs_with_size = []
        for audio_path, script_path in audio_script_pairs:
            audio_size = Path(audio_path).stat().st_size
            pairs_with_size.append((audio_size, audio_path, script_path))
        
        # Process largest files first to minimize idle time
        pairs_with_size.sort(reverse=True)
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = []
            
            for _, audio_path, script_path in pairs_with_size:
                future = executor.submit(
                    self._process_single_optimized, 
                    audio_path, script_path, output_dir
                )
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch processing error: {e}")
                    results.append({"error": str(e)})
        
        return results
    
    def _process_single_optimized(self, audio_path: str, script_path: str, 
                                output_dir: Path) -> Dict:
        """Process single file with optimizations."""
        # This would call the main align function with optimizations
        # Implementation would go here
        return {
            "audio_path": audio_path,
            "script_path": script_path,
            "status": "processed",
            "output_path": output_dir / f"{Path(audio_path).stem}.srt"
        }