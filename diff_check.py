#!/usr/bin/env python3
"""STEP 4 — Diff checker: compare generated SRT against biovera-vo-1.srt reference.

Run: .venv/bin/python diff_check.py [generated.srt]
     .venv/bin/python diff_check.py          # uses output/biovera-vo-1.srt
"""

import re
import sys
from pathlib import Path

REFERENCE_PATH = Path("input/biovera-vo-1.srt")
DEFAULT_OUTPUT = Path("output/biovera-vo-1.srt")


# ── SRT parsing ────────────────────────────────────────────────────────────

def _srt_time_to_ms(ts: str) -> int:
    """Convert HH:MM:SS,mmm to milliseconds."""
    ts = ts.strip()
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3_600_000 + int(m) * 60_000 + int(s) * 1_000 + int(ms)


def load_srt(path: Path) -> list[dict]:
    """Return list of {index, start_ms, end_ms, text} dicts."""
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\r?\n\r?\n", text.strip())
    segments = []
    for block in blocks:
        lines = [l.strip() for l in re.split(r"\r?\n", block.strip()) if l.strip()]
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0])
            start_str, end_str = lines[1].split(" --> ")
            caption_text = " ".join(lines[2:])
            segments.append({
                "index": idx,
                "start_ms": _srt_time_to_ms(start_str),
                "end_ms": _srt_time_to_ms(end_str),
                "text": caption_text,
            })
        except Exception:
            continue
    return segments


# ── Text similarity ────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Strip whitespace and fold case for comparison."""
    return re.sub(r"\s+", " ", text.strip()).lower()


def _char_similarity(a: str, b: str) -> float:
    """Jaccard character-level similarity (0-1)."""
    a, b = _normalize(a), _normalize(b)
    if a == b:
        return 1.0
    if not a and not b:
        return 1.0
    sa, sb = set(a), set(b)
    intersection = len(sa & sb)
    union = len(sa | sb)
    return intersection / union if union else 0.0


def _best_match(ref_block: dict, output_blocks: list[dict],
                time_window_ms: int = 3000) -> tuple[dict | None, float]:
    """Find best-matching output block using temporal proximity + text similarity.

    First restricts candidates to output blocks whose start_ms is within
    time_window_ms of the reference block start.  Among candidates, picks
    the one with the highest text similarity.  Falls back to global search
    if no temporal candidate matches.
    """
    ref_start = ref_block["start_ms"]

    def _score(ob: dict) -> float:
        return _char_similarity(ref_block["text"], ob["text"])

    # Primary: within temporal window
    candidates = [ob for ob in output_blocks
                  if abs(ob["start_ms"] - ref_start) <= time_window_ms]
    if candidates:
        best = max(candidates, key=_score)
        return best, _score(best)

    # Fallback: global best
    best = max(output_blocks, key=_score)
    return best, _score(best)


# ── Criteria checks ────────────────────────────────────────────────────────

MATCH_THRESHOLD = 0.5      # minimum similarity to count as "matched"
TIMESTAMP_TOLERANCE = 150  # ms — criterion 3


def run_diff(reference: list[dict], output: list[dict]) -> None:
    n_ref = len(reference)
    n_out = len(output)
    pct_count = n_out / n_ref if n_ref else 0

    print(f"\n{'='*60}")
    print(f"  DIFF CHECK REPORT")
    print(f"{'='*60}")
    print(f"  Reference blocks : {n_ref}")
    print(f"  Output blocks    : {n_out}  ({pct_count*100:.1f}% of reference)")

    # Match each reference block to best output block
    matched = 0
    deltas = []
    offenders = []

    for ref in reference:
        best, sim = _best_match(ref, output)
        if best and sim >= MATCH_THRESHOLD:
            matched += 1
            delta_start = abs(ref["start_ms"] - best["start_ms"])
            delta_end = abs(ref["end_ms"] - best["end_ms"])
            deltas.append((delta_start, delta_end, ref, best, sim))
        else:
            offenders.append((ref, None, sim))

    pct_matched = matched / n_ref if n_ref else 0
    within_150 = sum(1 for d, _, *_ in deltas if d <= TIMESTAMP_TOLERANCE) if deltas else 0
    pct_within = within_150 / matched if matched else 0

    avg_delta = (sum(d for d, *_ in deltas) / len(deltas)) if deltas else 0
    worst = sorted(deltas, key=lambda x: x[0], reverse=True)[:10]

    # Reference endpoints
    ref_first_start = reference[0]["start_ms"] if reference else 0
    ref_last_end = reference[-1]["end_ms"] if reference else 0
    out_first_start = output[0]["start_ms"] if output else 0
    out_last_end = output[-1]["end_ms"] if output else 0

    print(f"\n  ── CRITERIA SCORES ──────────────────────────────────")
    c1 = 0.9 <= pct_count <= 1.1
    print(f"  C1  Caption count ±10%          : {'✅' if c1 else '❌'}  {n_out} (target 168-206)")

    c2 = pct_matched >= 0.90
    print(f"  C2  >90% blocks matched by text : {'✅' if c2 else '❌'}  {pct_matched*100:.1f}%  ({matched}/{n_ref})")

    c3 = pct_within >= 0.85
    print(f"  C3  >85% within ±150ms start    : {'✅' if c3 else '❌'}  {pct_within*100:.1f}%  ({within_150}/{matched})")

    c4 = abs(out_first_start - ref_first_start) <= 200
    print(f"  C4  First caption ≤200ms offset : {'✅' if c4 else '❌'}  output={out_first_start}ms ref={ref_first_start}ms")

    c5 = abs(out_last_end - ref_last_end) <= 500
    print(f"  C5  Last caption ≤500ms offset  : {'✅' if c5 else '❌'}  output={out_last_end}ms ref={ref_last_end}ms")

    print(f"  C6  Arabic text unmodified      :  (manual check — see output SRT)")
    print(f"  C7  French tokens preserved     :  (manual check — see output SRT)")

    no_short = all(s["end_ms"] - s["start_ms"] >= 100 for s in output)
    overlaps = sum(
        1 for i in range(len(output) - 1)
        if output[i]["end_ms"] > output[i + 1]["start_ms"]
    )
    c8 = no_short and overlaps == 0
    print(f"  C8  No <100ms, no overlaps      : {'✅' if c8 else '❌'}  "
          f"short={not no_short}, overlaps={overlaps}")

    passed = sum([c1, c2, c3, c4, c5, c8])
    print(f"\n  SCORE: {passed}/6 automatic criteria passed")
    print(f"  Avg start-delta  : {avg_delta:.0f}ms")

    print(f"\n  ── WORST 10 OFFENDERS (by start-ms delta) ───────────")
    for delta_s, delta_e, ref, out, sim in worst:
        print(f"  [{ref['index']:3d}] δstart={delta_s:4d}ms δend={delta_e:4d}ms  "
              f"ref='{ref['text'][:30]}' out='{out['text'][:30]}'")

    if offenders:
        print(f"\n  ── UNMATCHED REFERENCE BLOCKS ({len(offenders)}) ─────────────")
        for ref, _, sim in offenders[:15]:
            print(f"  [{ref['index']:3d}] sim={sim:.2f}  '{ref['text'][:40]}'")
        if len(offenders) > 15:
            print(f"  ... and {len(offenders)-15} more")

    print(f"{'='*60}\n")


def main():
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT

    if not REFERENCE_PATH.exists():
        print(f"❌ Reference SRT not found: {REFERENCE_PATH}")
        sys.exit(1)
    if not output_path.exists():
        print(f"❌ Output SRT not found: {output_path}")
        sys.exit(1)

    reference = load_srt(REFERENCE_PATH)
    output = load_srt(output_path)

    print(f"Reference : {REFERENCE_PATH}")
    print(f"Output    : {output_path}")

    run_diff(reference, output)


if __name__ == "__main__":
    main()
