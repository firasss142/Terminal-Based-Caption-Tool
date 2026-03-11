"""Job lifecycle manager for the web UI.

Handles job creation, state tracking, background worker execution,
and SSE event queue bridging between the CPU-bound alignment thread
and the async FastAPI event loop.
"""

import asyncio
import concurrent.futures
import dataclasses
import json
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# ─── Job state ────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    QUEUED  = "queued"
    RUNNING = "running"
    DONE    = "done"
    FAILED  = "failed"


@dataclass
class Job:
    id: str
    status: JobStatus
    audio_path: Path
    script_path: Path
    upload_dir: Path                        # temp dir for this job's uploads
    output_path: Optional[Path] = None
    quality_metrics: Optional[dict] = None
    suggestions: Optional[List[str]] = None
    error: Optional[str] = None
    caption_count: int = 0
    audio_name: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    events: asyncio.Queue = field(default_factory=asyncio.Queue)


# ─── Manager ──────────────────────────────────────────────────────────────────

class JobManager:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    def get_job(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"Job {job_id!r} not found")
        return job

    async def create_job(self, audio_bytes: bytes, audio_filename: str,
                         script_bytes: bytes, script_filename: str) -> Job:
        job_id = str(uuid.uuid4())
        upload_dir = Path(tempfile.mkdtemp(prefix=f"captjob_{job_id[:8]}_"))

        audio_path = upload_dir / audio_filename
        script_path = upload_dir / script_filename

        audio_path.write_bytes(audio_bytes)
        script_path.write_bytes(script_bytes)

        job = Job(
            id=job_id,
            status=JobStatus.QUEUED,
            audio_path=audio_path,
            script_path=script_path,
            upload_dir=upload_dir,
            audio_name=audio_filename,
        )
        self._jobs[job_id] = job
        return job

    async def run_job(self, job_id: str, language: str = "ara",
                      offset_ms: int = 0, word_level: bool = True,
                      max_chars: int = 42) -> None:
        job = self.get_job(job_id)
        job.status = JobStatus.RUNNING
        loop = asyncio.get_event_loop()

        def emit(stage: str, message: str, pct: int, **extra):
            event = {"stage": stage, "message": message, "pct": pct, **extra}
            loop.call_soon_threadsafe(job.events.put_nowait, event)

        def worker():
            import sys
            from pathlib import Path as _Path

            # Make caption-tool root importable
            root = _Path(__file__).parent.parent
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))

            import tempfile as _tempfile
            from validator import validate_inputs
            from normalize import normalize_audio
            from aligner import align_word_level, align
            from srt_writer import write_srt
            from quality_analyzer import CaptionQualityAnalyzer

            try:
                # 1. Validate
                emit("validating", "Checking inputs…", 10)
                result = validate_inputs(job.audio_path, job.script_path)
                warnings = result.get("warnings", [])
                word_count = result.get("word_count", 0)
                duration = result.get("audio_duration_sec", 0)

                # 2. Normalize
                emit("normalizing",
                     f"Converting to 16 kHz WAV ({duration:.1f}s audio)…", 20)
                with _tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_wav = f.name
                normalize_audio(job.audio_path, temp_wav)

                # 3. Load script
                emit("loading_model", "Loading script + MMS_FA model…", 35)
                script_text = job.script_path.read_text(encoding="utf-8")
                sentences = [l.strip() for l in script_text.splitlines() if l.strip()]
                if not sentences:
                    raise ValueError("Script file contains no non-empty lines.")

                # 4. Align
                emit("aligning",
                     f"Aligning {word_count} words ({len(sentences)} sentences)…", 55)
                if word_level:
                    segments = align_word_level(temp_wav, sentences, language, max_chars)
                else:
                    segments = align(temp_wav, sentences, language)

                # 5. Offset
                if offset_ms != 0:
                    for seg in segments:
                        seg["start_ms"] = max(0, seg["start_ms"] + offset_ms)
                        seg["end_ms"] = max(seg["start_ms"] + 100,
                                            seg["end_ms"] + offset_ms)

                # 6. Write SRT
                emit("writing", "Writing SRT file…", 82)
                output_dir = root / "output"
                output_dir.mkdir(exist_ok=True)
                stem = _Path(job.audio_name).stem
                output_path = output_dir / f"{stem}.srt"
                write_srt(segments, output_path, apply_grouping=word_level)
                job.output_path = output_path
                job.caption_count = len(segments)

                # 7. Quality
                emit("quality", "Analysing quality…", 93)
                analyzer = CaptionQualityAnalyzer()
                metrics = analyzer.analyze_srt_quality(output_path)
                grade = metrics.get_quality_grade()
                job.quality_metrics = {
                    **dataclasses.asdict(metrics),
                    "grade": grade,
                }
                job.suggestions = analyzer.suggest_improvements(metrics)

                # 8. Clean up temp wav
                try:
                    _Path(temp_wav).unlink()
                except OSError:
                    pass

                job.status = JobStatus.DONE

                # Persist to history DB (failure must never break the pipeline)
                try:
                    from web import db as _db
                    _db.save_job(
                        job_name=_Path(job.audio_name).stem,
                        srt_content=output_path.read_text(encoding="utf-8"),
                    )
                except Exception:
                    pass

                emit("done",
                     f"{job.caption_count} captions generated · Grade {grade}",
                     100,
                     caption_count=job.caption_count,
                     grade=grade,
                     warnings=warnings,
                     output_filename=output_path.name)

            except Exception as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                emit("error", str(exc), 0)

        loop.run_in_executor(self._executor, worker)

    def cleanup_job(self, job_id: str) -> None:
        job = self._jobs.pop(job_id, None)
        if job and job.upload_dir.exists():
            shutil.rmtree(job.upload_dir, ignore_errors=True)
