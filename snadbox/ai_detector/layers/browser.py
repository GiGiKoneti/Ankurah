"""
layers/browser.py — Detects AI tool usage through browser window titles,
connection-table reverse-DNS matching, and screen color analysis.

Uses word-boundary regex for keyword matching and exact domain matching only.
"""

import re
import socket
import time
import threading
from typing import Dict, List, Optional, Tuple

from config import AI_WINDOW_KEYWORDS, AI_DOMAINS, AI_PORTS, INTERNAL_HOSTS, AI_INTERFACE_COLORS
from capability import caps, _is_internal_service

# ─── Reverse-DNS cache (thread-safe) ─────────────────────────────────────────
_rdns_cache: Dict[str, Tuple[Optional[str], float]] = {}  # ip → (hostname, timestamp)
_rdns_lock   = threading.Lock()
_RDNS_TTL    = 60.0   # seconds before a cache entry expires

# Pre-compile keyword patterns with word boundaries for accurate matching
_KW_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
    for kw in AI_WINDOW_KEYWORDS
]


# ─── Window title helpers ─────────────────────────────────────────────────────

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

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )
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
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            titles.append(result.stdout.strip())
    except Exception:
        pass

    try:
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


# ─── Sub-scanner 1 — Window title scan ───────────────────────────────────────

def _scan_window_titles() -> Tuple[int, List[str]]:
    """Match window titles against AI_WINDOW_KEYWORDS using word-boundary regex."""
    titles = _get_all_window_titles()
    matched_keywords: set = set()
    evidence: List[str] = []

    for title in titles:
        for i, pattern in enumerate(_KW_PATTERNS):
            kw = AI_WINDOW_KEYWORDS[i]
            if kw not in matched_keywords and pattern.search(title):
                matched_keywords.add(kw)
                evidence.append(
                    f"Window title contains AI keyword '{kw}': {title[:80]}"
                )

    score = min(len(matched_keywords) * 4, 10)
    return score, evidence


# ─── Reverse-DNS helper ───────────────────────────────────────────────────────

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
        hostname = None   # cache the miss
    except Exception as e:
        print(f"[BROWSER] reverse DNS error for {ip}: {e}")
        hostname = None
    finally:
        socket.setdefaulttimeout(old_timeout)

    with _rdns_lock:
        _rdns_cache[ip] = (hostname, now)  # store None misses too
    return hostname


def _domain_matches(hostname: str, domain: str) -> bool:
    """Return True if hostname exactly matches domain or is a subdomain of it."""
    return hostname == domain or hostname.endswith("." + domain)


# ─── Sub-scanner 2 — Connection scan ─────────────────────────────────────────

def _scan_connections() -> Tuple[int, List[str]]:
    """Scan active network connections; exact-match reverse-DNS against AI_DOMAINS."""
    if not caps.can_read_connections:
        return 0, []

    import psutil  # type: ignore

    matched_domains: set = set()
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
            if not remote_ip:
                continue
            # Skip internal hosts
            if remote_ip in INTERNAL_HOSTS or remote_ip.startswith("127.") or remote_ip == "::1":
                continue
            # Skip if connection belongs to an internal service
            try:
                if conn.pid:
                    import psutil as _psutil
                    proc = _psutil.Process(conn.pid)
                    if _is_internal_service(proc):
                        continue
            except Exception:
                pass

            # Check IP cache first
            try:
                from db.ai_domains import get_domain_for_ip
                domain = get_domain_for_ip(remote_ip)
            except Exception:
                domain = None

            if domain is not None:
                if domain not in matched_domains:
                    matched_domains.add(domain)
                    evidence.append(
                        f"Connection to AI domain {domain} (IP {remote_ip})"
                    )
            else:
                # Live reverse-DNS with exact match only
                hostname = _resolve_rdns(remote_ip)
                if hostname:
                    for ai_domain in AI_DOMAINS:
                        if _domain_matches(hostname, ai_domain) and ai_domain not in matched_domains:
                            matched_domains.add(ai_domain)
                            evidence.append(
                                f"Connection to AI domain {ai_domain} via {hostname} (IP {remote_ip})"
                            )
        except Exception as e:
            print(f"[BROWSER] connection scan inner error: {e}")
            continue

    score = min(len(matched_domains) * 5, 10)
    return score, evidence


# ─── Sub-scanner 3 — Screen color analysis ────────────────────────────────────

def _scan_screen_color() -> Tuple[int, List[str]]:
    """Capture the top 100px of the screen and check for AI interface color signatures.

    Windows: BitBlt via ctypes. Linux: subprocess import or Pillow ImageGrab.
    Never does OCR — only checks color histograms for known AI UI signatures.
    """
    if caps.os_name == "Windows":
        return _scan_screen_color_windows()
    elif caps.os_name == "Linux":
        return _scan_screen_color_linux()
    return 0, []


def _scan_screen_color_windows() -> Tuple[int, List[str]]:
    """Use ctypes BitBlt to capture top 100px on Windows."""
    evidence: List[str] = []
    try:
        import ctypes
        import ctypes.wintypes

        # Screen dimensions
        user32 = ctypes.windll.user32
        gdi32  = ctypes.windll.gdi32
        screen_width  = user32.GetSystemMetrics(0)
        capture_height = 100

        hdc_screen = user32.GetDC(0)
        hdc_mem    = gdi32.CreateCompatibleDC(hdc_screen)
        bitmap     = gdi32.CreateCompatibleBitmap(hdc_screen, screen_width, capture_height)
        gdi32.SelectObject(hdc_mem, bitmap)
        SRCCOPY = 0x00CC0020
        gdi32.BitBlt(hdc_mem, 0, 0, screen_width, capture_height, hdc_screen, 0, 0, SRCCOPY)

        # Sample pixels at regular intervals
        sample_points = [(x, y) for x in range(0, screen_width, 20) for y in range(0, 100, 10)]
        color_counts: Dict[str, int] = {}

        for x, y in sample_points:
            try:
                pixel = gdi32.GetPixel(hdc_mem, x, y)
                r = pixel & 0xFF
                g = (pixel >> 8) & 0xFF
                b = (pixel >> 16) & 0xFF
                for name, (tr, tg, tb) in AI_INTERFACE_COLORS.items():
                    if abs(r - tr) < 15 and abs(g - tg) < 15 and abs(b - tb) < 15:
                        color_counts[name] = color_counts.get(name, 0) + 1
            except Exception:
                pass

        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)

        for name, count in color_counts.items():
            if count >= 5:  # threshold: at least 5 matching pixels
                evidence.append(
                    f"AI interface color detected: {name} pattern in tab area "
                    f"({count} matching pixels)"
                )
                return 4, evidence

    except Exception as e:
        print(f"[BROWSER] screen color Windows error: {e}")
    return 0, evidence


def _scan_screen_color_linux() -> Tuple[int, List[str]]:
    """Use Pillow or xwd-based capture of top 100px on Linux."""
    evidence: List[str] = []
    try:
        try:
            from PIL import ImageGrab  # type: ignore
            img = ImageGrab.grab(bbox=(0, 0, 1920, 100))
        except Exception:
            return 0, []  # Pillow not available or headless

        color_counts: Dict[str, int] = {}
        pixels = img.getdata()
        for pixel in pixels:
            if len(pixel) >= 3:
                r, g, b = pixel[0], pixel[1], pixel[2]
                for name, (tr, tg, tb) in AI_INTERFACE_COLORS.items():
                    if abs(r - tr) < 15 and abs(g - tg) < 15 and abs(b - tb) < 15:
                        color_counts[name] = color_counts.get(name, 0) + 1

        for name, count in color_counts.items():
            if count >= 5:
                evidence.append(
                    f"AI interface color detected: {name} pattern in tab area "
                    f"({count} matching pixels)"
                )
                return 4, evidence

    except Exception as e:
        print(f"[BROWSER] screen color Linux error: {e}")
    return 0, evidence


# ─── ForensicEvent converter ──────────────────────────────────────────────────

def to_forensic_events(scan_result: dict) -> list:
    """Convert a browser layer result dict into a list of ForensicEvent objects."""
    events = []
    try:
        from api import push_event
        from shared.schemas import ForensicEvent

        score    = scan_result.get("score", 0)
        value    = min(score / 10.0, 1.0)
        severity = (
            "critical" if score >= 8 else
            "high"     if score >= 6 else
            "medium"   if score >= 3 else "low"
        )

        for ev_str in scan_result.get("evidence", []):
            signal = (
                "screen_ai_interface" if "color detected" in ev_str else
                "ai_domain"           if "domain" in ev_str.lower() else
                "stealth_window"      if "Window title" in ev_str else
                "browser"
            )
            event = ForensicEvent(
                timestamp=time.time(),
                source="varchas",
                layer=scan_result.get("layer", "browser"),
                signal=signal,
                value=value,
                raw=scan_result.get("raw", {}),
                severity=severity,
                description=ev_str,
            )
            events.append(event)
    except Exception as e:
        print(f"[BROWSER] to_forensic_events error: {e}")
    return events


# ─── Public API ───────────────────────────────────────────────────────────────

def run_browser_scan() -> dict:
    """Run window-title + connection + screen color scans; return standard layer result dict."""
    all_evidence: List[str] = []
    raw: dict = {}

    title_score, title_evidence = 0, []
    conn_score,  conn_evidence  = 0, []
    screen_score, screen_ev     = 0, []

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

    try:
        screen_score, screen_ev = _scan_screen_color()
        all_evidence.extend(screen_ev)
        raw["screen_color_matches"] = screen_ev
        raw["screen_color_score"]   = screen_score
    except Exception as e:
        print(f"[BROWSER] screen color scan error: {e}")
        raw["screen_error"] = str(e)

    final_score = min(title_score + conn_score + screen_score, 10)

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
