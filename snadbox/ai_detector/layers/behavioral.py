"""
layers/behavioral.py — Detects AI usage through clipboard monitoring.

A background daemon thread polls the clipboard every 200ms. Paste events are
analysed for size and AI-written style heuristics. run_behavioral_scan()
returns evidence from the last 30 seconds only.
"""

import hashlib
import re
import threading
import time
from typing import List, Dict, Any

from config import PASTE_CHAR_THRESHOLD, POLL_INTERVAL_FAST, HEURISTIC_MIN_CHARS
from capability import caps

# ─── Shared state (thread-safe) ───────────────────────────────────────────────
_clipboard_events: List[Dict[str, Any]] = []
_clipboard_lock   = threading.Lock()
_monitor_started  = False


# ─── Heuristic AI text analyser ───────────────────────────────────────────────

_AI_OPENERS = [
    "certainly",
    "of course",
    "here's",
    "here is",
    "as an ai",
    "i'd be happy",
    "i would be happy",
    "sure!",
    "absolutely",
    "to answer your question",
    "great question",
    "i'm glad you asked",
]

_CONTRACTION_RE = re.compile(
    r"\b(i'm|you're|we're|they're|it's|that's|don't|can't|won't|isn't"
    r"|aren't|wasn't|weren't|didn't|doesn't|haven't|hasn't|hadn't"
    r"|i've|you've|we've|they've|i'll|you'll|we'll|they'll|i'd|you'd"
    r"|we'd|they'd|he's|she's|let's)\b",
    re.IGNORECASE,
)

_MARKDOWN_RE = re.compile(r"(#+\s|\*\*[^*]+\*\*|`[^`]+`|\|\s*[-:]+\s*\|)")

_NUMBERED_LIST_RE   = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
_BULLETED_LIST_RE   = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)


def _heuristic_score(text: str) -> int:
    """Score text for AI-written style; returns integer score (2+ = ai_style_text)."""
    score = 0

    # Numbered or bulleted lists
    if _NUMBERED_LIST_RE.search(text) or _BULLETED_LIST_RE.search(text):
        score += 1

    # Formal opener phrases
    text_lower = text.lower()
    for phrase in _AI_OPENERS:
        if phrase in text_lower:
            score += 2
            break  # only count once

    # Long text with very few contractions
    if len(text) > 500:
        contraction_count = len(_CONTRACTION_RE.findall(text))
        word_count        = len(text.split())
        if word_count > 0 and (contraction_count / word_count) < 0.005:
            score += 1

    # Markdown formatting
    if _MARKDOWN_RE.search(text):
        score += 1

    return score


# ─── Background thread ────────────────────────────────────────────────────────

def _clipboard_monitor_loop() -> None:
    """Poll clipboard every POLL_INTERVAL_FAST seconds; record paste events."""
    last_content: str = ""

    while True:
        try:
            import pyperclip  # type: ignore
            try:
                current = pyperclip.paste()
            except Exception as e:
                print(f"[BEHAVIORAL] pyperclip.paste error: {e}")
                time.sleep(POLL_INTERVAL_FAST)
                continue

            if current != last_content:
                now   = time.time()
                size  = len(current)
                chash = hashlib.sha256(current.encode("utf-8", errors="replace")).hexdigest()[:16]

                large_paste = size > PASTE_CHAR_THRESHOLD
                hs          = _heuristic_score(current) if size >= HEURISTIC_MIN_CHARS else 0
                ai_style    = hs >= 2

                event: Dict[str, Any] = {
                    "timestamp":    now,
                    "size":         size,
                    "content_hash": chash,
                    "large_paste":  large_paste,
                    "heuristic_score": hs,
                    "ai_style_text": ai_style,
                }

                with _clipboard_lock:
                    _clipboard_events.append(event)
                    # Keep only last 300 events to bound memory
                    if len(_clipboard_events) > 300:
                        _clipboard_events[:] = _clipboard_events[-300:]

                last_content = current

        except Exception as e:
            print(f"[BEHAVIORAL] clipboard monitor loop error: {e}")

        time.sleep(POLL_INTERVAL_FAST)


def start_clipboard_monitor() -> None:
    """Start the clipboard polling thread (daemon, safe to call multiple times)."""
    global _monitor_started
    if _monitor_started:
        return
    if not caps.has_clipboard:
        print("[BEHAVIORAL] Clipboard not available — monitor not started")
        return

    t = threading.Thread(
        target=_clipboard_monitor_loop,
        name="clipboard-monitor",
        daemon=True,
    )
    t.start()
    _monitor_started = True
    print("[BEHAVIORAL] Clipboard monitor started")


# ─── Public API ───────────────────────────────────────────────────────────────

def run_behavioral_scan() -> dict:
    """Return clipboard events from the last 30 seconds as a layer result dict."""
    cutoff = time.time() - 30.0
    score  = 0
    evidence: List[str] = []
    raw: Dict[str, Any] = {}

    try:
        with _clipboard_lock:
            recent = [e for e in _clipboard_events if e["timestamp"] >= cutoff]

        raw["events_last_30s"] = len(recent)
        raw["paste_events"]    = recent

        for event in recent:
            if event.get("large_paste"):
                score = min(score + 5, 10)
                evidence.append(
                    f"Large clipboard paste: {event['size']} chars "
                    f"(hash: {event['content_hash']})"
                )
            if event.get("ai_style_text"):
                score = min(score + 4, 10)
                evidence.append(
                    f"AI-style text detected in paste "
                    f"(heuristic score: {event['heuristic_score']})"
                )

    except Exception as e:
        print(f"[BEHAVIORAL] run_behavioral_scan error: {e}")
        raw["error"] = str(e)

    confidence = 1.0 if caps.has_clipboard else 0.0

    return {
        "layer":      "behavioral",
        "score":      score,
        "evidence":   evidence,
        "confidence": round(confidence, 2),
        "raw":        raw,
    }
