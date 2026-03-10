#!/usr/bin/env python3
"""Robust resume-capable downloader for the ctc-forced-aligner ONNX model."""
import os, ssl, sys, time, urllib.request
from pathlib import Path

URL = "https://huggingface.co/deskpai/ctc_forced_aligner/resolve/main/04ac86b67129634da93aea76e0147ef3.onnx"
MODEL_PATH = Path.home() / "ctc_forced_aligner" / "model.onnx"
TOTAL_SIZE = 1_262_421_764   # bytes

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

attempt = 0
while True:
    attempt += 1
    current = MODEL_PATH.stat().st_size if MODEL_PATH.exists() else 0
    if current >= TOTAL_SIZE:
        print(f"✅ Model complete: {current:,} bytes")
        break

    pct = current / TOTAL_SIZE * 100
    print(f"[attempt {attempt}] Resuming from {current:,} bytes ({pct:.1f}%)...")
    req = urllib.request.Request(URL, headers={"Range": f"bytes={current}-"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=60)
        mode = "ab" if current > 0 else "wb"
        with open(MODEL_PATH, mode) as f:
            chunk_size = 1024 * 1024  # 1 MB
            downloaded = current
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                done = downloaded / TOTAL_SIZE * 100
                sys.stdout.write(f"\r  {downloaded//1024//1024} MB / {TOTAL_SIZE//1024//1024} MB  ({done:.1f}%)  ")
                sys.stdout.flush()
        print()
    except Exception as e:
        print(f"\n  Error: {e} — retrying in 5s...")
        time.sleep(5)
