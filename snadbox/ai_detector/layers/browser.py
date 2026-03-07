"""
layers/browser.py — Detects AI tool usage through browser window titles
and connection-table reverse-DNS matching.

Two independent sub-methods are combined into a single run_browser_scan().
"""

import socket
import time
import threading
from typing import Dict, List, Optional, Tuple

from config import AI_WINDOW_KEYWORDS, AI_DOMAINS, AI_PORTS
from capability import caps

# ─── Reverse-DNS cache (thread-safe) ─────────────────────────────────────────
_rdns_cache: Dict[str, Tuple[Optional[str], float]] = {}  # ip → (hostname, timestamp)
_rdns_lock   = threading.Lock()
_RDNS_TTL    = 60.0   # seconds before a cache entry expires


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _get_window_titles_windows() -> List[str]:
    """Enumerate all visible window titles on Windows via ctypes user32."""
    titles: List[str] = []
    try:
        import ctypes
        import ctypes.wintypes

        titles_ref: List[str] = []

        def _enum_handler(hwnd, _lParam):
            try:
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                    if buf.value.strip():
                        titles_ref.append(buf.value)
            except Exception:
                pass
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        ctypes.windll.user32.EnumWindows(EnumWindowsProc(_enum_handler), 0)
        titles = titles_ref
    except Exception as e:
        print(f"[BROWSER] Windows window enum error: {e}")
    return titles


def _get_window_titles_linux() -> List[str]:
    """Retrieve visible window titles on Linux using xdotool or wmctrl."""
    import subprocess
    titles: List[str] = []
    try:
        # Prefer xdotool for active window
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            titles.append(result.stdout.strip())
    except Exception:
        pass

    try:
        # wmctrl -l lists all windows: id desktop pid title
        result = subprocess.run(
            ["wmctrl", "-l"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split(None, 3)
                if len(parts) == 4:
                    titles.append(parts[3])
    except Exception as e:
        print(f"[BROWSER] wmctrl error: {e}")
    return titles


def _get_window_titles_mac() -> List[str]:
    """Retrieve all application window names on macOS via osascript."""
    import subprocess
    titles: List[str] = []
    try:
        script = 'tell application "System Events" to get name of every window of every process'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            # Output is comma-separated nested lists; flatten
            raw = result.stdout.replace("{", "").replace("}", "").replace('"', "")
            titles = [t.strip() for t in raw.split(",") if t.strip()]
    except Exception as e:
        print(f"[BROWSER] macOS osascript error: {e}")
    return titles


def _get_all_window_titles() -> List[str]:
    """Return all visible window titles for the current platform."""
    if not caps.has_window_api:
        return []
    try:
        if caps.os_name == "Windows":
            return _get_window_titles_windows()
        elif caps.os_name == "Linux":
            return _get_window_titles_linux()
        elif caps.os_name == "Darwin":
            return _get_window_titles_mac()
    except Exception as e:
        print(f"[BROWSER] window title collection error: {e}")
    return []


def _scan_window_titles() -> Tuple[int, List[str]]:
    """Match window titles against AI_WINDOW_KEYWORDS and return (score, evidence)."""
    titles = _get_all_window_titles()
    matched_keywords = set()
    evidence: List[str] = []

    for title in titles:
        title_lower = title.lower()
        for kw in AI_WINDOW_KEYWORDS:
            if kw in title_lower and kw not in matched_keywords:
                matched_keywords.add(kw)
                evidence.append(f"Window title contains AI keyword '{kw}': {title[:60]}")

    score = min(len(matched_keywords) * 4, 10)
    return score, evidence


def _resolve_rdns(ip: str) -> Optional[str]:
    """Perform a cached reverse-DNS lookup with 1s timeout; returns hostname or None."""
    now = time.monotonic()
    with _rdns_lock:
        cached = _rdns_cache.get(ip)
        if cached is not None:
            hostname, ts = cached
            if now - ts < _RDNS_TTL:
                return hostname  # may be None (cached miss)

    hostname: Optional[str] = None
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(1.0)
    try:
        result = socket.gethostbyaddr(ip)
        hostname = result[0]
    except (socket.herror, socket.gaierror, socket.timeout, OSError):
        hostname = None   # cache the miss — don't retry for TTL seconds
    except Exception as e:
        print(f"[BROWSER] reverse DNS error for {ip}: {e}")
        hostname = None
    finally:
        socket.setdefaulttimeout(old_timeout)

    with _rdns_lock:
        _rdns_cache[ip] = (hostname, now)  # store None misses too
    return hostname


def _scan_connections() -> Tuple[int, List[str]]:
    """Scan active network connections; reverse-DNS match against AI_DOMAINS."""
    if not caps.can_read_connections:
        return 0, []

    import psutil  # type: ignore

    matched_domains = set()
    evidence: List[str] = []

    try:
        conns = psutil.net_connections(kind="inet")
    except psutil.AccessDenied:
        print("[BROWSER] AccessDenied reading net_connections")
        return 0, []
    except Exception as e:
        print(f"[BROWSER] net_connections error: {e}")
        return 0, []

    for conn in conns:
        try:
            if not conn.raddr:
                continue
            remote_ip = conn.raddr.ip
            if not remote_ip or remote_ip.startswith("127.") or remote_ip == "::1":
                continue

            # Check the IP cache first (populated by db/ai_domains.py)
            try:
                from db.ai_domains import get_domain_for_ip
                domain = get_domain_for_ip(remote_ip)
            except Exception:
                domain = None

            if domain is None:
                # Fall back to live reverse-DNS
                hostname = _resolve_rdns(remote_ip)
                if hostname:
                    for ai_domain in AI_DOMAINS:
                        if ai_domain in hostname and ai_domain not in matched_domains:
                            matched_domains.add(ai_domain)
                            evidence.append(f"Connection to AI domain {ai_domain} (IP {remote_ip})")
            else:
                if domain not in matched_domains:
                    matched_domains.add(domain)
                    evidence.append(f"Connection to AI domain {domain} (IP {remote_ip})")
        except Exception as e:
            print(f"[BROWSER] connection scan inner error: {e}")
            continue

    score = min(len(matched_domains) * 5, 10)
    return score, evidence


# ─── Public API ───────────────────────────────────────────────────────────────

def run_browser_scan() -> dict:
    """Run window-title + connection-table scans; return standard layer result dict."""
    all_evidence: List[str] = []
    raw: dict = {}

    title_score, title_evidence = 0, []
    conn_score,  conn_evidence  = 0, []

    try:
        title_score, title_evidence = _scan_window_titles()
        all_evidence.extend(title_evidence)
        raw["title_matches"] = title_evidence
        raw["title_score"]   = title_score
    except Exception as e:
        print(f"[BROWSER] window title scan error: {e}")
        raw["title_error"] = str(e)

    try:
        conn_score, conn_evidence = _scan_connections()
        all_evidence.extend(conn_evidence)
        raw["conn_matches"] = conn_evidence
        raw["conn_score"]   = conn_score
    except Exception as e:
        print(f"[BROWSER] connection scan error: {e}")
        raw["conn_error"] = str(e)

    final_score = min(title_score + conn_score, 10)

    # Confidence drops if we couldn't read connections or window titles
    confidence = 1.0
    if not caps.has_window_api:
        confidence -= 0.25
    if not caps.can_read_connections:
        confidence -= 0.25

    return {
        "layer":      "browser",
        "score":      final_score,
        "evidence":   all_evidence,
        "confidence": max(round(confidence, 2), 0.0),
        "raw":        raw,
    }
