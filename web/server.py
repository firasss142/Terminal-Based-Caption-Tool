"""FastAPI server for the RT Caption Generator web UI."""

import json
import sys
from pathlib import Path
from typing import List

# Make caption-tool root importable (for config constants used in form defaults)
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import DEFAULT_LANGUAGE, MAX_CHARS_PER_LINE
from web import db
from web.job_manager import JobManager, JobStatus

# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(title="RT Caption Generator", docs_url=None, redoc_url=None)
manager = JobManager()


@app.on_event("startup")
async def startup():
    db.init_db()

_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return FileResponse(str(_STATIC / "index.html"))


# ─── Job: create (single file) ────────────────────────────────────────────────

@app.post("/api/jobs/single")
async def create_single_job(
    audio: UploadFile = File(...),
    script: UploadFile = File(...),
    language: str = Form(default=DEFAULT_LANGUAGE),
    offset_ms: int = Form(default=0),
    word_level: bool = Form(default=True),
    max_chars: int = Form(default=MAX_CHARS_PER_LINE),
):
    audio_bytes = await audio.read()
    script_bytes = await script.read()

    if not audio_bytes:
        raise HTTPException(400, "Audio file is empty")
    if not script_bytes:
        raise HTTPException(400, "Script file is empty")

    job = await manager.create_job(
        audio_bytes=audio_bytes,
        audio_filename=audio.filename or "audio.mp3",
        script_bytes=script_bytes,
        script_filename=script.filename or "script.txt",
    )

    # Fire-and-forget in background (non-blocking)
    await manager.run_job(job.id, language=language, offset_ms=offset_ms,
                          word_level=word_level, max_chars=max_chars)

    return {"job_id": job.id, "audio_name": job.audio_name}


# ─── Job: create (batch) ──────────────────────────────────────────────────────

@app.post("/api/jobs/batch")
async def create_batch_job(
    files: List[UploadFile] = File(...),
    language: str = Form(default=DEFAULT_LANGUAGE),
    offset_ms: int = Form(default=0),
    word_level: bool = Form(default=True),
    max_chars: int = Form(default=MAX_CHARS_PER_LINE),
):
    """Create a batch job for processing multiple audio/script pairs."""
    
    # Group files by stem (filename without extension)
    file_groups = {}
    
    for file in files:
        if not file.filename:
            continue
            
        file_path = Path(file.filename)
        stem = file_path.stem
        ext = file_path.suffix.lower()
        
        if stem not in file_groups:
            file_groups[stem] = {}
            
        if ext in ['.mp3', '.wav', '.m4a', '.aac']:
            file_groups[stem]['audio'] = file
        elif ext == '.txt':
            file_groups[stem]['script'] = file
    
    # Find valid pairs (both audio and script)
    valid_pairs = []
    for stem, group in file_groups.items():
        if 'audio' in group and 'script' in group:
            valid_pairs.append((stem, group['audio'], group['script']))
    
    if not valid_pairs:
        raise HTTPException(400, "No valid audio/script pairs found. Files should have matching names (e.g., video1.mp3 + video1.txt)")
    
    # Create batch job ID
    import uuid
    batch_id = str(uuid.uuid4())
    
    # Create individual jobs for each pair
    batch_jobs = []
    for stem, audio_file, script_file in valid_pairs:
        audio_bytes = await audio_file.read()
        script_bytes = await script_file.read()
        
        if not audio_bytes:
            raise HTTPException(400, f"Audio file {audio_file.filename} is empty")
        if not script_bytes:
            raise HTTPException(400, f"Script file {script_file.filename} is empty")
        
        job = await manager.create_job(
            audio_bytes=audio_bytes,
            audio_filename=audio_file.filename or f"{stem}.mp3",
            script_bytes=script_bytes,
            script_filename=script_file.filename or f"{stem}.txt",
        )
        
        batch_jobs.append({
            "job_id": job.id,
            "stem": stem,
            "audio_name": job.audio_name,
            "status": "pending"
        })
    
    # Process jobs sequentially in background
    import asyncio
    asyncio.create_task(process_batch_jobs(batch_jobs, language, offset_ms, word_level, max_chars))
    
    return {
        "batch_id": batch_id,
        "job_count": len(batch_jobs),
        "jobs": batch_jobs
    }


async def process_batch_jobs(batch_jobs, language, offset_ms, word_level, max_chars):
    """Process batch jobs sequentially."""
    for job_info in batch_jobs:
        try:
            await manager.run_job(
                job_info["job_id"],
                language=language,
                offset_ms=offset_ms,
                word_level=word_level,
                max_chars=max_chars
            )
            job_info["status"] = "completed"
        except Exception as e:
            job_info["status"] = "failed"
            job_info["error"] = str(e)


# ─── Job: SSE progress stream ─────────────────────────────────────────────────

@app.get("/api/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    try:
        job = manager.get_job(job_id)
    except KeyError:
        raise HTTPException(404, f"Job {job_id!r} not found")

    async def event_gen():
        # Keep-alive comment first so the browser recognises the SSE stream
        yield ": connected\n\n"
        while True:
            event = await job.events.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("stage") in ("done", "error"):
                break

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if any
        },
    )


# ─── Job: status snapshot (polling fallback) ──────────────────────────────────

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    try:
        job = manager.get_job(job_id)
    except KeyError:
        raise HTTPException(404, f"Job {job_id!r} not found")

    return {
        "job_id": job.id,
        "status": job.status,
        "caption_count": job.caption_count,
        "error": job.error,
        "output_filename": job.output_path.name if job.output_path else None,
    }


# ─── Job: download SRT ────────────────────────────────────────────────────────

@app.get("/api/jobs/{job_id}/download")
async def download_srt(job_id: str):
    try:
        job = manager.get_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")

    if job.status != JobStatus.DONE or not job.output_path:
        raise HTTPException(409, "SRT file not ready yet")

    if not job.output_path.exists():
        raise HTTPException(410, "SRT file has been removed from disk")

    return FileResponse(
        str(job.output_path),
        media_type="application/x-subrip",
        filename=job.output_path.name,
        headers={
            "Content-Disposition": f'attachment; filename="{job.output_path.name}"'
        },
    )


# ─── Job: quality metrics ─────────────────────────────────────────────────────

@app.get("/api/jobs/{job_id}/quality")
async def get_quality(job_id: str):
    try:
        job = manager.get_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")

    if job.quality_metrics is None:
        raise HTTPException(409, "Quality analysis not complete yet")

    return {
        "metrics": job.quality_metrics,
        "suggestions": job.suggestions or [],
    }


# ─── Job: cleanup ─────────────────────────────────────────────────────────────

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    try:
        manager.cleanup_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found")
    return {"deleted": job_id}


# ─── History: list all completed jobs ─────────────────────────────────────────

@app.get("/history")
async def get_history():
    return db.list_jobs()


# ─── History: download SRT by DB id ───────────────────────────────────────────

@app.get("/download/{job_id}")
async def download_from_history(job_id: int):
    from fastapi.responses import Response
    srt = db.get_srt(job_id)
    if srt is None:
        raise HTTPException(404, "Job not found in history")
    jobs = db.list_jobs()
    row = next((j for j in jobs if j["id"] == job_id), None)
    filename = f"{row['job_name']}.srt" if row else f"job_{job_id}.srt"
    return Response(
        content=srt,
        media_type="application/x-subrip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── History: delete a job ─────────────────────────────────────────────────────

@app.delete("/job/{job_id}")
async def delete_history_job(job_id: int):
    if not db.delete_job(job_id):
        raise HTTPException(404, "Job not found in history")
    return {"deleted": job_id}
