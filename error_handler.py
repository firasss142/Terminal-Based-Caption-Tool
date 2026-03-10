"""Enhanced error handling and recovery mechanisms."""

import logging
import traceback
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for classification."""
    LOW = "low"          # Warnings, non-critical issues
    MEDIUM = "medium"    # Recoverable errors
    HIGH = "high"        # Critical errors requiring user intervention
    FATAL = "fatal"      # Unrecoverable errors


class CaptionToolError(Exception):
    """Base exception class for caption tool errors."""
    
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.severity = severity
        self.suggestions = suggestions or []
        
    def get_user_message(self) -> str:
        """Get user-friendly error message with suggestions."""
        msg = f"❌ {self.severity.value.upper()}: {str(self)}"
        
        if self.suggestions:
            msg += "\n\n💡 Suggestions:"
            for i, suggestion in enumerate(self.suggestions, 1):
                msg += f"\n  {i}. {suggestion}"
        
        return msg


class AudioValidationError(CaptionToolError):
    """Errors related to audio file validation."""
    pass


class ScriptValidationError(CaptionToolError):
    """Errors related to script file validation."""
    pass


class AlignmentError(CaptionToolError):
    """Errors during the alignment process."""
    pass


class ModelError(CaptionToolError):
    """Errors related to model loading/downloading."""
    pass


class ErrorRecovery:
    """Error recovery and retry mechanisms."""
    
    @staticmethod
    @contextmanager
    def retry_on_failure(max_retries: int = 3, delay: float = 1.0,
                        exceptions: tuple = (Exception,)):
        """Retry operation with exponential backoff."""
        import time
        
        for attempt in range(max_retries + 1):
            try:
                yield attempt
                break
            except exceptions as e:
                if attempt == max_retries:
                    raise
                
                wait_time = delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. "
                             f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
    
    @staticmethod
    def diagnose_alignment_failure(audio_path: Path, script_path: Path) -> List[str]:
        """Diagnose common alignment failure causes."""
        suggestions = []
        
        # Check file sizes
        audio_size = audio_path.stat().st_size
        script_size = script_path.stat().st_size
        
        if audio_size < 1024:  # Very small audio file
            suggestions.append("Audio file seems too small - ensure it contains speech")
        
        if script_size < 10:  # Very small script
            suggestions.append("Script file seems too short - ensure it contains text")
        
        # Check script content
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if len(content.split()) < 5:
                suggestions.append("Script contains very few words - alignment may be unreliable")
            
            if not any('\u0600' <= c <= '\u06FF' for c in content):
                suggestions.append("Script contains no Arabic text - ensure language setting is correct")
                
        except Exception:
            suggestions.append("Cannot read script file - check encoding (should be UTF-8)")
        
        # Audio duration check
        try:
            import subprocess
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 
                  'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                  str(audio_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            duration = float(result.stdout.strip())
            
            if duration < 1.0:
                suggestions.append("Audio is very short - ensure it contains sufficient speech")
            elif duration > 300:  # 5 minutes
                suggestions.append("Audio is very long - consider splitting into smaller segments")
                
        except Exception:
            suggestions.append("Cannot determine audio duration - ensure file is valid")
        
        return suggestions
    
    @staticmethod
    def suggest_recovery_actions(error: Exception, context: Dict[str, Any]) -> List[str]:
        """Suggest recovery actions based on error type and context."""
        suggestions = []
        error_str = str(error).lower()
        
        if "memory" in error_str or "out of memory" in error_str:
            suggestions.extend([
                "Free up system memory by closing other applications",
                "Try processing smaller audio segments",
                "Use sentence-level alignment instead of word-level",
                "Restart the script to clear memory"
            ])
        
        elif "network" in error_str or "connection" in error_str or "download" in error_str:
            suggestions.extend([
                "Check your internet connection",
                "Try again in a few minutes (server may be busy)",
                "Use a VPN if in a restricted network",
                "Clear the model cache directory and retry"
            ])
        
        elif "permission" in error_str or "access" in error_str:
            suggestions.extend([
                "Check file permissions for input/output directories",
                "Run as administrator if necessary",
                "Ensure output directory is writable"
            ])
        
        elif "format" in error_str or "codec" in error_str:
            suggestions.extend([
                "Convert audio to a supported format (MP3, WAV, M4A)",
                "Ensure audio has speech content (not just music/silence)",
                "Check if audio file is corrupted"
            ])
        
        elif "alignment failed" in error_str:
            audio_path = context.get('audio_path')
            script_path = context.get('script_path')
            
            if audio_path and script_path:
                suggestions.extend(
                    ErrorRecovery.diagnose_alignment_failure(audio_path, script_path)
                )
        
        return suggestions


class ErrorLogger:
    """Enhanced error logging with context."""
    
    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file or Path("caption_tool_errors.log")
        
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log error with full context and stack trace."""
        context = context or {}
        
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "stack_trace": traceback.format_exc()
        }
        
        # Log to file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                import json
                import datetime
                
                log_entry = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    **error_info
                }
                f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n\n")
                
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")
        
        # Log to console
        logger.error(f"Error: {error_info['error_type']}: {error_info['error_message']}")
        if context:
            logger.error(f"Context: {context}")


def handle_graceful_shutdown(error: Exception, context: Dict[str, Any] = None) -> str:
    """Handle graceful shutdown with user-friendly error reporting."""
    context = context or {}
    
    # Log the error
    error_logger = ErrorLogger()
    error_logger.log_error(error, context)
    
    # Determine error type and provide appropriate response
    if isinstance(error, CaptionToolError):
        return error.get_user_message()
    
    # For other exceptions, create a generic CaptionToolError
    suggestions = ErrorRecovery.suggest_recovery_actions(error, context)
    
    if "memory" in str(error).lower():
        severity = ErrorSeverity.HIGH
    elif "network" in str(error).lower() or "download" in str(error).lower():
        severity = ErrorSeverity.MEDIUM
    else:
        severity = ErrorSeverity.HIGH
    
    wrapped_error = CaptionToolError(
        message=str(error),
        severity=severity,
        suggestions=suggestions
    )
    
    return wrapped_error.get_user_message()