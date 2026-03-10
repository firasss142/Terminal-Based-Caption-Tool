"""Quality analysis and validation for generated captions."""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional
from dataclasses import dataclass

from config import (
    MIN_CAPTION_DURATION_MS, GAP_BETWEEN_CAPTIONS_MS, 
    MAX_CHARS_PER_LINE, MAX_GAP_WARNING_MS
)


@dataclass
class QualityMetrics:
    """Quality metrics for caption analysis."""
    total_captions: int
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    overlapping_count: int
    short_caption_count: int
    long_caption_count: int
    avg_chars_per_caption: float
    gaps_too_large: int
    timing_accuracy_score: float  # 0.0 - 1.0
    
    def get_quality_grade(self) -> str:
        """Get overall quality grade A-F."""
        score = self.timing_accuracy_score
        
        # Penalize for issues
        penalty = 0
        penalty += (self.overlapping_count / self.total_captions) * 0.3
        penalty += (self.short_caption_count / self.total_captions) * 0.2
        penalty += (self.gaps_too_large / self.total_captions) * 0.1
        
        final_score = max(0.0, score - penalty)
        
        if final_score >= 0.9:
            return "A"
        elif final_score >= 0.8:
            return "B" 
        elif final_score >= 0.7:
            return "C"
        elif final_score >= 0.6:
            return "D"
        else:
            return "F"


class CaptionQualityAnalyzer:
    """Analyzes caption quality and provides improvement suggestions."""
    
    def __init__(self):
        self.arabic_pattern = re.compile(r'[\u0600-\u06FF]+')
        self.french_pattern = re.compile(r'[a-zA-ZÀ-ÿ]+')
    
    def analyze_srt_quality(self, srt_path: Union[str, Path]) -> QualityMetrics:
        """Analyze SRT file quality and return comprehensive metrics."""
        segments = self._parse_srt_file(srt_path)
        
        if not segments:
            raise ValueError("No segments found in SRT file")
        
        durations = [seg['end_ms'] - seg['start_ms'] for seg in segments]
        char_counts = [len(seg['text']) for seg in segments]
        
        # Calculate basic metrics
        total_captions = len(segments)
        avg_duration = sum(durations) / total_captions
        min_duration = min(durations)
        max_duration = max(durations)
        avg_chars = sum(char_counts) / total_captions
        
        # Count quality issues
        overlapping_count = self._count_overlapping_segments(segments)
        short_caption_count = sum(1 for d in durations if d < MIN_CAPTION_DURATION_MS)
        long_caption_count = sum(1 for chars in char_counts if chars > MAX_CHARS_PER_LINE)
        gaps_too_large = self._count_large_gaps(segments)
        
        # Calculate timing accuracy score
        timing_score = self._calculate_timing_accuracy(segments)
        
        return QualityMetrics(
            total_captions=total_captions,
            avg_duration_ms=avg_duration,
            min_duration_ms=min_duration,
            max_duration_ms=max_duration,
            overlapping_count=overlapping_count,
            short_caption_count=short_caption_count,
            long_caption_count=long_caption_count,
            avg_chars_per_caption=avg_chars,
            gaps_too_large=gaps_too_large,
            timing_accuracy_score=timing_score
        )
    
    def _parse_srt_file(self, srt_path: Union[str, Path]) -> List[Dict]:
        """Parse SRT file into segments."""
        segments = []
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Split into subtitle blocks
        blocks = content.split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
                
            try:
                # Parse timing line (format: 00:00:00,000 --> 00:00:00,000)
                timing_line = lines[1]
                start_str, end_str = timing_line.split(' --> ')
                
                start_ms = self._time_to_ms(start_str)
                end_ms = self._time_to_ms(end_str)
                
                # Text is everything after the timing line
                text = '\n'.join(lines[2:]).strip()
                
                segments.append({
                    'index': len(segments) + 1,
                    'start_ms': start_ms,
                    'end_ms': end_ms,
                    'text': text
                })
                
            except (ValueError, IndexError) as e:
                continue  # Skip malformed blocks
        
        return segments
    
    def _time_to_ms(self, time_str: str) -> int:
        """Convert SRT time format to milliseconds."""
        # Format: HH:MM:SS,mmm
        time_part, ms_part = time_str.split(',')
        h, m, s = map(int, time_part.split(':'))
        ms = int(ms_part)
        
        return ((h * 3600 + m * 60 + s) * 1000) + ms
    
    def _count_overlapping_segments(self, segments: List[Dict]) -> int:
        """Count segments that overlap in time."""
        overlapping = 0
        
        for i in range(len(segments) - 1):
            current_end = segments[i]['end_ms']
            next_start = segments[i + 1]['start_ms']
            
            if current_end > next_start:
                overlapping += 1
        
        return overlapping
    
    def _count_large_gaps(self, segments: List[Dict]) -> int:
        """Count gaps between segments that are too large."""
        large_gaps = 0
        
        for i in range(len(segments) - 1):
            current_end = segments[i]['end_ms']
            next_start = segments[i + 1]['start_ms']
            gap = next_start - current_end
            
            if gap > MAX_GAP_WARNING_MS:
                large_gaps += 1
        
        return large_gaps
    
    def _calculate_timing_accuracy(self, segments: List[Dict]) -> float:
        """Calculate timing accuracy score based on various factors."""
        if not segments:
            return 0.0
        
        scores = []
        
        # Score based on duration distribution
        durations = [seg['end_ms'] - seg['start_ms'] for seg in segments]
        avg_duration = sum(durations) / len(durations)
        
        for duration in durations:
            # Ideal duration is around 1000-3000ms for readability
            if 1000 <= duration <= 3000:
                scores.append(1.0)
            elif 500 <= duration < 1000 or 3000 < duration <= 5000:
                scores.append(0.7)
            elif 100 <= duration < 500 or 5000 < duration <= 8000:
                scores.append(0.4)
            else:
                scores.append(0.1)
        
        return sum(scores) / len(scores)
    
    def analyze_text_patterns(self, segments: List[Dict]) -> Dict[str, any]:
        """Analyze text patterns in the captions."""
        arabic_count = 0
        french_count = 0
        mixed_count = 0
        empty_count = 0
        
        for segment in segments:
            text = segment['text'].strip()
            
            if not text:
                empty_count += 1
                continue
            
            has_arabic = bool(self.arabic_pattern.search(text))
            has_french = bool(self.french_pattern.search(text))
            
            if has_arabic and has_french:
                mixed_count += 1
            elif has_arabic:
                arabic_count += 1
            elif has_french:
                french_count += 1
        
        total = len(segments)
        
        return {
            "arabic_only": arabic_count,
            "french_only": french_count,
            "mixed_language": mixed_count,
            "empty_captions": empty_count,
            "arabic_percentage": (arabic_count / total) * 100 if total > 0 else 0,
            "mixed_percentage": (mixed_count / total) * 100 if total > 0 else 0,
        }
    
    def suggest_improvements(self, metrics: QualityMetrics, 
                           text_analysis: Optional[Dict] = None) -> List[str]:
        """Suggest specific improvements based on analysis."""
        suggestions = []
        
        if metrics.overlapping_count > 0:
            suggestions.append(
                f"Fix {metrics.overlapping_count} overlapping captions - "
                "use gap correction or adjust timing"
            )
        
        if metrics.short_caption_count > metrics.total_captions * 0.1:  # >10%
            suggestions.append(
                f"{metrics.short_caption_count} captions are too short (<{MIN_CAPTION_DURATION_MS}ms) - "
                "consider grouping words or using sentence-level alignment"
            )
        
        if metrics.long_caption_count > 0:
            suggestions.append(
                f"{metrics.long_caption_count} captions exceed {MAX_CHARS_PER_LINE} characters - "
                "enable auto-splitting or reduce max-chars setting"
            )
        
        if metrics.gaps_too_large > 0:
            suggestions.append(
                f"{metrics.gaps_too_large} gaps between captions are too large - "
                "check for silent periods in audio or misaligned segments"
            )
        
        if metrics.avg_duration_ms < 500:
            suggestions.append(
                "Average caption duration is very short - "
                "consider using sentence-level instead of word-level alignment"
            )
        
        if metrics.avg_duration_ms > 5000:
            suggestions.append(
                "Average caption duration is too long - "
                "use word-level alignment or reduce max-chars limit"
            )
        
        grade = metrics.get_quality_grade()
        if grade in ['D', 'F']:
            suggestions.append(
                f"Overall quality grade: {grade} - "
                "consider re-running with different alignment settings"
            )
        
        return suggestions
    
    def compare_alignment_modes(self, word_level_srt: Path, 
                              sentence_level_srt: Path) -> Dict[str, any]:
        """Compare word-level vs sentence-level alignment quality."""
        word_metrics = self.analyze_srt_quality(word_level_srt)
        sentence_metrics = self.analyze_srt_quality(sentence_level_srt)
        
        return {
            "word_level": {
                "grade": word_metrics.get_quality_grade(),
                "caption_count": word_metrics.total_captions,
                "avg_duration": word_metrics.avg_duration_ms,
                "issues": word_metrics.overlapping_count + word_metrics.short_caption_count
            },
            "sentence_level": {
                "grade": sentence_metrics.get_quality_grade(),
                "caption_count": sentence_metrics.total_captions,
                "avg_duration": sentence_metrics.avg_duration_ms,
                "issues": sentence_metrics.overlapping_count + sentence_metrics.short_caption_count
            },
            "recommendation": self._recommend_best_mode(word_metrics, sentence_metrics)
        }
    
    def _recommend_best_mode(self, word_metrics: QualityMetrics, 
                           sentence_metrics: QualityMetrics) -> str:
        """Recommend the best alignment mode based on metrics."""
        word_grade = word_metrics.get_quality_grade()
        sentence_grade = sentence_metrics.get_quality_grade()
        
        grade_values = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}
        
        word_score = grade_values.get(word_grade, 0)
        sentence_score = grade_values.get(sentence_grade, 0)
        
        if word_score > sentence_score:
            return f"Word-level recommended (Grade {word_grade} vs {sentence_grade})"
        elif sentence_score > word_score:
            return f"Sentence-level recommended (Grade {sentence_grade} vs {word_grade})"
        else:
            # Same grades - consider other factors
            if word_metrics.avg_duration_ms < 1000:
                return "Sentence-level recommended (word captions too short)"
            elif sentence_metrics.avg_duration_ms > 8000:
                return "Word-level recommended (sentence captions too long)"
            else:
                return f"Both modes similar quality (Grade {word_grade}) - choose based on preference"