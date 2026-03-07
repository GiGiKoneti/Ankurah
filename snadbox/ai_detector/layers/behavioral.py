"""
layers/behavioral.py — Detects AI usage through clipboard monitoring,
keyboard timing analysis, and question-answer latency profiling.

A background daemon thread polls the clipboard every 100ms. Paste events are
analysed for size and AI-written style heuristics. A pynput keyboard listener
records only timing metadata (never actual keys). run_behavioral_scan()
returns evidence from the last 30 seconds only.
"""

import collections
import hashlib
import re
import threading
import time
from typing import List, Dict, Any, Deque

from config import (
    PASTE_CHAR_THRESHOLD, POLL_INTERVAL_FAST, HEURISTIC_MIN_CHARS,
    TYPING_BURST_WPM, LATENCY_AI_STD, LATENCY_HUMAN_STD, MIN_LATENCY_SAMPLES,
)
from capability import caps

# ─── Shared state (thread-safe) ───────────────────────────────────────────────
_clipboard_events: List[Dict[str, Any]] = []
_clipboard_lock   = threading.Lock()
_monitor_started  = False

# ─── Typing behavior state ────────────────────────────────────────────────────
_keystroke_times: Deque[float] = collections.deque(maxlen=500)
_backspace_count  = 0
_total_key_count  = 0
_paste_burst_times: Deque[float] = collections.deque(maxlen=20)
_typing_lock      = threading.Lock()
_keyboard_started = False

# ─── Q&A Latency profiling ────────────────────────────────────────────────────
_latency_samples: Deque[float] = collections.deque(maxlen=50)
_last_answer_event_ts: float = 0.0
_latency_lock = threading.Lock()


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

_MARKDOWN_RE       = re.compile(r"(#+\s|\*\*[^*]+\*\*|`[^`]+`|\|\s*[-:]+\s*\|)")
_NUMBERED_LIST_RE  = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
_BULLETED_LIST_RE  = re.compile(r"^\s*[-*•]\s+", re.MULTILINE)


def _heuristic_score(text: str) -> int:
    """Score text for AI-written style; returns integer score (2+ = ai_style_text)."""
    score = 0

    if _NUMBERED_LIST_RE.search(text) or _BULLETED_LIST_RE.search(text):
        score += 1

    text_lower = text.lower()
    for phrase in _AI_OPENERS:
        if phrase in text_lower:
            score += 2
            break

    if len(text) > 500:
        contraction_count = len(_CONTRACTION_RE.findall(text))
        word_count        = len(text.split())
        if word_count > 0 and (contraction_count / word_count) < 0.005:
            score += 1

    if _MARKDOWN_RE.search(text):
        score += 1

    return score


# ─── Background clipboard thread ──────────────────────────────────────────────

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
                chash = hashlib.sha256(
                    current.encode("utf-8", errors="replace")
                ).hexdigest()[:16]

                large_paste = size > PASTE_CHAR_THRESHOLD
                hs          = _heuristic_score(current) if size >= HEURISTIC_MIN_CHARS else 0
                ai_style    = hs >= 2

                event: Dict[str, Any] = {
                    "timestamp":       now,
                    "size":            size,
                    "content_hash":    chash,
                    "large_paste":     large_paste,
                    "heuristic_score": hs,
                    "ai_style_text":   ai_style,
                }

                with _clipboard_lock:
                    _clipboard_events.append(event)
                    if len(_clipboard_events) > 300:
                        _clipboard_events[:] = _clipboard_events[-300:]

                # Track paste burst timing
                with _typing_lock:
                    _paste_burst_times.append(now)

                last_content = current

                # Immediately push ForensicEvent on large paste
                if large_paste:
                    _push_paste_event(event)

        except Exception as e:
            print(f"[BEHAVIORAL] clipboard monitor loop error: {e}")

        time.sleep(POLL_INTERVAL_FAST)


def _push_paste_event(event: dict) -> None:
    """Push a large paste ForensicEvent immediately to the api queue."""
    try:
        from api import push_event
        from shared.schemas import ForensicEvent
        push_event(ForensicEvent(
            timestamp=event["timestamp"],
            source="varchas",
            layer="behavioral",
            signal="large_paste",
            value=min(event["size"] / 5000.0, 1.0),
            raw={"size": event["size"], "content_hash": event["content_hash"]},
            severity="high" if event.get("ai_style_text") else "medium",
            description=(
                f"Large clipboard paste: {event['size']} chars "
                f"(hash: {event['content_hash']})"
            ),
        ))
    except Exception:
        pass


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
    print("[STARTUP] Clipboard monitor started")


# ─── Keyboard listener (pynput) ───────────────────────────────────────────────

def _on_key_press(key) -> None:
    """Record keystroke timing metadata — never the actual key value."""
    now = time.monotonic()
    try:
        with _typing_lock:
            global _total_key_count, _backspace_count
            _total_key_count += 1
            _keystroke_times.append(now)

            # Detect backspace (pynput Key.backspace)
            try:
                from pynput.keyboard import Key  # type: ignore
                if key == Key.backspace:
                    _backspace_count += 1
            except Exception:
                pass
    except Exception:
        pass


def start_keyboard_listener() -> None:
    """Start the pynput keyboard listener to record timing metadata only."""
    global _keyboard_started
    if _keyboard_started:
        return
    try:
        from pynput.keyboard import Listener  # type: ignore

        def _listener_thread() -> None:
            while True:
                try:
                    with Listener(on_press=_on_key_press) as listener:
                        listener.join()
                except Exception as e:
                    print(f"[BEHAVIORAL] keyboard listener error: {e}")
                    time.sleep(2.0)

        t = threading.Thread(
            target=_listener_thread,
            name="keyboard-listener",
            daemon=True,
        )
        t.start()
        _keyboard_started = True
        print("[STARTUP] Keyboard listener started")
    except Exception as e:
        print(f"[BEHAVIORAL] Could not start keyboard listener: {e}")


# ─── Typing behavior analysis ─────────────────────────────────────────────────

def _scan_typing_behavior() -> Dict[str, Any]:
    """Analyse recorded keystroke timing for AI-assisted paste patterns."""
    result: Dict[str, Any] = {
        "inter_key_delay_ms": [],
        "paste_burst_5s":     0,
        "backspace_rate":     0.0,
        "typing_burst_flag":  False,
        "ai_paste_flag":      False,
        "score_contribution": 0,
        "evidence":           [],
    }

    try:
        with _typing_lock:
            times  = list(_keystroke_times)
            bp     = list(_paste_burst_times)
            total  = _total_key_count
            backs  = _backspace_count

        if len(times) >= 2:
            delays = [
                (times[i] - times[i - 1]) * 1000  # ms
                for i in range(1, len(times))
                if 0 < (times[i] - times[i - 1]) < 2.0
            ]
            result["inter_key_delay_ms"] = delays[:20]

            if delays:
                avg_delay_ms = sum(delays) / len(delays)
                # Characters per minute: 1000ms / avg_delay * 60
                cpm = (1000.0 / avg_delay_ms) * 60 if avg_delay_ms > 0 else 0
                wpm = cpm / 5.0
                if wpm > TYPING_BURST_WPM:
                    result["typing_burst_flag"] = True
                    result["score_contribution"] += 3
                    result["evidence"].append(
                        f"Typing burst detected: {wpm:.0f} WPM (>{TYPING_BURST_WPM} = likely paste)"
                    )

        # Backspace rate
        if total > 20:
            bk_rate = backs / total
            result["backspace_rate"] = round(bk_rate, 3)
            # < 5% backspace on substantial typing = AI pasted
            if bk_rate < 0.05:
                result["ai_paste_flag"] = True
                result["score_contribution"] += 2
                result["evidence"].append(
                    f"Low backspace rate {bk_rate:.1%} on {total} keystrokes — AI paste pattern"
                )

        # Paste burst: multiple pastes within 5 seconds
        now5 = time.time()
        recent_pastes = [t for t in bp if now5 - t < 5.0]
        result["paste_burst_5s"] = len(recent_pastes)
        if len(recent_pastes) >= 3:
            result["score_contribution"] += 3
            result["evidence"].append(
                f"Paste burst: {len(recent_pastes)} pastes in last 5 seconds"
            )

    except Exception as e:
        print(f"[BEHAVIORAL] _scan_typing_behavior error: {e}")

    return result


# ─── Q&A Latency profiling ────────────────────────────────────────────────────

def record_answer_event() -> None:
    """Record a Q&A answer event timestamp for latency profiling.

    Call this externally when an answer window is detected.
    """
    global _last_answer_event_ts
    try:
        now = time.time()
        with _latency_lock:
            if _last_answer_event_ts > 0:
                latency = now - _last_answer_event_ts
                if 0.1 < latency < 120.0:  # sane range: 100ms to 2 minutes
                    _latency_samples.append(latency)
            _last_answer_event_ts = now
    except Exception as e:
        print(f"[BEHAVIORAL] record_answer_event error: {e}")


def _scan_latency_profile() -> Dict[str, Any]:
    """Analyse Q&A response latency for AI-consistent timing patterns."""
    result: Dict[str, Any] = {
        "samples":            0,
        "mean_latency_s":     0.0,
        "std_latency_s":      0.0,
        "ai_consistent":      False,
        "score_contribution": 0,
        "evidence":           [],
    }

    try:
        with _latency_lock:
            samples = list(_latency_samples)

        result["samples"] = len(samples)
        if len(samples) < MIN_LATENCY_SAMPLES:
            return result

        mean = sum(samples) / len(samples)
        variance = sum((x - mean) ** 2 for x in samples) / len(samples)
        std  = variance ** 0.5

        result["mean_latency_s"] = round(mean, 3)
        result["std_latency_s"]  = round(std, 3)

        if std < LATENCY_AI_STD:
            result["ai_consistent"] = True
            result["score_contribution"] += 3
            result["evidence"].append(
                f"AI-consistent response timing: std={std:.2f}s < {LATENCY_AI_STD}s "
                f"over {len(samples)} samples (suspiciously uniform)"
            )

    except Exception as e:
        print(f"[BEHAVIORAL] _scan_latency_profile error: {e}")

    return result


# ─── ForensicEvent converter ──────────────────────────────────────────────────

def to_forensic_events(scan_result: dict) -> list:
    """Convert a behavioral layer result dict into a list of ForensicEvent objects."""
    events = []
    try:
        from api import push_event
        from shared.schemas import ForensicEvent

        score = scan_result.get("score", 0)
        value = min(score / 10.0, 1.0)
        severity = (
            "critical" if score >= 8 else
            "high"     if score >= 6 else
            "medium"   if score >= 3 else "low"
        )

        for ev_str in scan_result.get("evidence", []):
            signal = (
                "large_paste"   if "paste" in ev_str.lower() else
                "ai_style_text" if "AI-style" in ev_str else
                "typing_burst"  if "burst" in ev_str.lower() else
                "behavioral"
            )
            event = ForensicEvent(
                timestamp=time.time(),
                source="varchas",
                layer=scan_result.get("layer", "behavioral"),
                signal=signal,
                value=value,
                raw=scan_result.get("raw", {}),
                severity=severity,
                description=ev_str,
            )
            events.append(event)
    except Exception as e:
        print(f"[BEHAVIORAL] to_forensic_events error: {e}")
    return events


# ─── Public API ───────────────────────────────────────────────────────────────

def run_behavioral_scan() -> dict:
    """Return clipboard, typing, and latency events from the last 30 seconds as a layer result dict."""
    cutoff = time.time() - 30.0
    score  = 0
    evidence: List[str] = []
    raw: Dict[str, Any] = {}

    try:
        # ── Clipboard events ────────────────────────────────────────
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
        print(f"[BEHAVIORAL] clipboard scan error: {e}")
        raw["clipboard_error"] = str(e)

    try:
        # ── Typing behavior ─────────────────────────────────────────
        typing_data = _scan_typing_behavior()
        raw["typing"] = typing_data
        contrib = typing_data.get("score_contribution", 0)
        score = min(score + contrib, 10)
        evidence.extend(typing_data.get("evidence", []))
    except Exception as e:
        print(f"[BEHAVIORAL] typing scan error: {e}")

    try:
        # ── Q&A latency ─────────────────────────────────────────────
        latency_data = _scan_latency_profile()
        raw["latency_profile"] = latency_data
        contrib = latency_data.get("score_contribution", 0)
        score = min(score + contrib, 10)
        evidence.extend(latency_data.get("evidence", []))
    except Exception as e:
        print(f"[BEHAVIORAL] latency scan error: {e}")

    confidence = 1.0 if caps.has_clipboard else 0.0

    return {
        "layer":      "behavioral",
        "score":      score,
        "evidence":   evidence,
        "confidence": round(confidence, 2),
        "raw":        raw,
    }
