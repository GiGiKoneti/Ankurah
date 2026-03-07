"""
layers/process.py — Detects AI tool usage via process names, loaded DLLs,
listening ports, and model file access events.

Sub-scanners: process/DLL, port listen, threat processes, WMI discrepancy,
and watchdog model-file watcher. All loops skip internal TruthLens services.
"""

import os
import time
import threading
from typing import List, Dict, Any

import psutil  # type: ignore

from config import (
    AI_PROCESS_NAMES, AI_DLLS, AI_PORTS, RAM_SPIKE_MB,
    AI_MODEL_EXTENSIONS, THREAT_PROCESSES, INTERNAL_PORTS,
)
from capability import caps, _is_internal_service

# ─── Model-file watcher (watchdog) ───────────────────────────────────────────

_model_hits: List[Dict[str, Any]] = []
_model_hits_lock = threading.Lock()
_watcher_started = False


class _ModelFileHandler:
    """Watchdog event handler that records accesses to AI model files."""

    def dispatch(self, event):
        """Handle any filesystem event; check for model file extensions."""
        try:
            path = getattr(event, "src_path", "") or ""
            _, ext = os.path.splitext(path.lower())
            if ext in AI_MODEL_EXTENSIONS:
                with _model_hits_lock:
                    _model_hits.append({
                        "path":      path,
                        "timestamp": time.time(),
                    })
        except Exception as e:
            print(f"[PROCESS] model file handler error: {e}")

    def on_any_event(self, event):
        """Forward all events to dispatch."""
        self.dispatch(event)


def start_model_file_watcher() -> None:
    """Start the watchdog observer in a daemon thread to monitor model file access."""
    global _watcher_started
    if _watcher_started:
        return
    try:
        from watchdog.observers import Observer  # type: ignore
        from watchdog.events import FileSystemEventHandler  # type: ignore

        class _WatchdogHandler(FileSystemEventHandler):
            """Watchdog-native handler that delegates to _ModelFileHandler."""
            def __init__(self):
                super().__init__()
                self._inner = _ModelFileHandler()

            def on_any_event(self, event):
                """Forward all events to the inner handler."""
                self._inner.on_any_event(event)

        observer = Observer()

        # Targeted directories — only where AI models actually live
        candidates = [
            os.path.join(os.path.expanduser("~"), ".ollama", "models"),
            os.path.join(os.path.expanduser("~"), ".cache", "lm-studio", "models"),
            os.path.join(os.path.expanduser("~"), "models"),
            os.path.join(os.path.expanduser("~"), "Models"),
            os.path.join(os.path.expanduser("~"), "AppData", "Roaming",
                         "LM Studio", "models"),
            os.environ.get("TEMP", ""),
            "/tmp",
        ]

        watch_dirs = [d for d in candidates if d and os.path.isdir(d)]

        if not watch_dirs:
            print("[PROCESS] No model directories found — file watcher idle")
            return

        handler = _WatchdogHandler()
        for d in watch_dirs:
            try:
                observer.schedule(handler, d, recursive=True)
            except Exception as e:
                print(f"[PROCESS] watchdog schedule error for {d}: {e}")

        observer.daemon = True
        observer.start()
        _watcher_started = True
        print("[STARTUP] Model file watcher started")
    except Exception as e:
        print(f"[PROCESS] Could not start watchdog observer: {e}")


def get_model_file_hits() -> List[Dict[str, Any]]:
    """Return model file access events from the last 60 seconds only."""
    cutoff = time.time() - 60.0
    try:
        with _model_hits_lock:
            recent = [h for h in _model_hits if h["timestamp"] >= cutoff]
            _model_hits[:] = recent
            return list(recent)
    except Exception as e:
        print(f"[PROCESS] get_model_file_hits error: {e}")
        return []


# ─── Sub-scanner 1 — Process name + DLL scan ─────────────────────────────────

def _scan_processes() -> tuple:
    """Scan running processes for AI names, loaded DLLs, CPU, and RAM usage.

    Returns (score, evidence, raw_list).
    """
    score    = 0
    evidence: List[str] = []
    raw_procs: List[Dict] = []

    try:
        for proc in psutil.process_iter(
            ["pid", "name", "exe", "cmdline", "cpu_percent", "memory_info", "ppid"]
        ):
            try:
                # Skip internal TruthLens services
                if _is_internal_service(proc):
                    continue

                name    = (proc.info.get("name") or "").lower()
                exe     = (proc.info.get("exe") or "").lower()
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                mem     = proc.info.get("memory_info")
                rss_mb  = mem.rss / (1024 * 1024) if mem else 0
                cpu_pct = proc.info.get("cpu_percent") or 0.0

                proc_data: Dict[str, Any] = {
                    "pid":    proc.pid,
                    "name":   proc.info.get("name"),
                    "exe":    proc.info.get("exe"),
                    "ppid":   proc.info.get("ppid"),
                    "rss_mb": round(rss_mb, 1),
                    "cpu_pct": round(cpu_pct, 1),
                    "flags":  [],
                }

                # Check process name against AI_PROCESS_NAMES
                name_match = any(
                    ai.lower() in name or ai.lower() in cmdline
                    for ai in AI_PROCESS_NAMES
                )
                if name_match:
                    proc_data["flags"].append("AI_PROCESS_NAME")
                    score = min(score + 3, 10)
                    evidence.append(f"AI process '{proc.info.get('name')}' (PID {proc.pid})")

                # Check loaded memory maps for AI DLLs
                try:
                    maps = proc.memory_maps()
                    for mmap in maps:
                        mpath = (mmap.path or "").lower()
                        for dll in AI_DLLS:
                            if dll.lower() in mpath:
                                proc_data["flags"].append(f"DLL:{dll}")
                                score = min(score + 4, 10)
                                evidence.append(
                                    f"AI DLL '{dll}' loaded by '{proc.info.get('name')}' (PID {proc.pid})"
                                )
                                break
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
                except Exception as e:
                    print(f"[PROCESS] memory_maps error PID {proc.pid}: {e}")

                if proc_data["flags"]:
                    raw_procs.append(proc_data)

            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except psutil.AccessDenied:
                continue
            except Exception as e:
                print(f"[PROCESS] process scan inner error: {e}")
                continue

    except Exception as e:
        print(f"[PROCESS] process_iter error: {e}")

    return score, evidence, raw_procs


# ─── Sub-scanner 2 — Listening port scan ─────────────────────────────────────

def _scan_ports() -> tuple:
    """Check listening TCP ports against AI_PORTS; skip INTERNAL_PORTS.

    Returns (score, evidence, raw).
    """
    score    = 0
    evidence: List[str] = []
    raw_ports: List[Dict] = []

    if not caps.can_read_connections:
        return 0, [], []

    try:
        conns = psutil.net_connections(kind="inet")
        for conn in conns:
            try:
                if conn.status != psutil.CONN_LISTEN:
                    continue
                port = conn.laddr.port if conn.laddr else None
                if port is None:
                    continue
                # Skip our own internal service ports
                if port in INTERNAL_PORTS:
                    continue
                if port in AI_PORTS:
                    service = AI_PORTS[port]
                    # Identify owning process
                    proc_name = ""
                    try:
                        if conn.pid:
                            proc_name = psutil.Process(conn.pid).name()
                    except Exception:
                        pass
                    score = min(score + 8, 10)
                    evidence.append(
                        f"AI service listening on port {port}: {service}"
                        + (f" (proc: {proc_name})" if proc_name else "")
                    )
                    raw_ports.append({
                        "port":      port,
                        "service":   service,
                        "proc_name": proc_name,
                        "pid":       conn.pid,
                    })
            except Exception as e:
                print(f"[PROCESS] port scan inner error: {e}")
    except psutil.AccessDenied:
        print("[PROCESS] AccessDenied on net_connections (port scan)")
    except Exception as e:
        print(f"[PROCESS] port scan error: {e}")

    return score, evidence, raw_ports


# ─── Sub-scanner 3 — Varchas Threat Processes ────────────────────────────────

def _scan_threat_processes() -> tuple:
    """Scan running processes for blacklisted cheating/tunneling Varchas threats.

    Returns (score, evidence, raw_list). Pushes critical ForensicEvents immediately.
    """
    score    = 0
    evidence: List[str] = []
    raw_list: List[Dict] = []

    try:
        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                # Skip internal TruthLens services
                if _is_internal_service(proc):
                    continue

                name = (proc.info.get("name") or "").lower()
                exe  = (proc.info.get("exe") or "").lower()
                pid  = proc.pid

                for frag, (label, severity) in THREAT_PROCESSES.items():
                    if frag in name or frag in exe:
                        entry = {
                            "pid":       pid,
                            "name":      proc.info.get("name") or "",
                            "exe":       proc.info.get("exe"),
                            "cmdline":   " ".join(proc.info.get("cmdline") or [])[:200],
                            "label":     label,
                            "severity":  severity,
                            "match_key": frag,
                        }
                        raw_list.append(entry)

                        if severity == "critical":
                            score = min(score + 9, 10)
                        elif severity == "high":
                            score = min(score + 6, 10)

                        ev_str = (
                            f"THREAT: {label} ({severity}) — "
                            f"process '{proc.info.get('name') or ''}' PID {pid}"
                        )
                        evidence.append(ev_str)

                        # Immediately push ForensicEvent on critical find
                        if severity == "critical":
                            _push_critical_event(ev_str, score, entry)

                        break  # Only trigger once per process

            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                print(f"[PROCESS] threat scan inner error: {e}")
                continue
    except Exception as e:
        print(f"[PROCESS] threat scan error: {e}")

    return score, evidence, raw_list


def _push_critical_event(description: str, score: int, raw: dict) -> None:
    """Push a critical ForensicEvent to the api event queue immediately."""
    try:
        from api import push_event
        import time
        from shared.schemas import ForensicEvent
        push_event(ForensicEvent(
            timestamp=time.time(),
            source="varchas",
            layer="process",
            signal="threat_process",
            value=min(score / 10.0, 1.0),
            raw=raw,
            severity="critical",
            description=description,
        ))
    except Exception:
        pass  # Queue push is best-effort; never crash the scanner


# ─── Sub-scanner 4 — WMI Discrepancy (Windows only) ─────────────────────────

def _scan_wmi_discrepancy() -> tuple:
    """Detect hidden/renamed processes visible to WMI but missed/altered in psutil.

    Returns (score, evidence, raw). Always returns zeros on Linux/Mac.
    """
    if caps.os_name != "Windows":
        return 0, [], {}

    score    = 0
    evidence: List[str] = []
    raw: Dict[str, Any] = {"hidden": [], "renamed": []}

    try:
        import wmi  # type: ignore
        c = wmi.WMI()

        psutil_map: Dict[int, str] = {}
        for p in psutil.process_iter(["pid", "name"]):
            psutil_map[p.pid] = p.info.get("name") or ""

        wmi_map: Dict[int, str] = {}
        for p in c.Win32_Process():
            try:
                wmi_map[int(p.ProcessId)] = p.Name
            except Exception:
                continue

        # PIDs in WMI but not psutil = hidden process
        for pid, wmi_name in wmi_map.items():
            if pid in (0, 4):  # System/Idle — always present
                continue
            if pid not in psutil_map:
                score = min(score + 7, 10)
                ev_str = (
                    f"Hidden process: WMI='{wmi_name}' PID {pid} "
                    f"not visible to psutil — possible evasion"
                )
                evidence.append(ev_str)
                raw["hidden"].append({"pid": pid, "wmi_name": wmi_name})
            else:
                ps_name  = psutil_map[pid]
                wn_lower = (wmi_name or "").lower().strip()
                pn_lower = ps_name.lower().strip()
                if (len(wn_lower) >= 4 and len(pn_lower) >= 4
                        and not wn_lower.startswith(pn_lower[:4])
                        and not pn_lower.startswith(wn_lower[:4])):
                    score = min(score + 7, 10)
                    evidence.append(
                        f"Renamed process: WMI='{wmi_name}' vs psutil='{ps_name}' PID {pid}"
                    )
                    raw["renamed"].append({
                        "pid": pid, "wmi_name": wmi_name, "ps_name": ps_name
                    })

    except ImportError:
        pass
    except Exception as e:
        print(f"[PROCESS] WMI discrepancy scan error: {e}")
        raw["error"] = str(e)

    return score, evidence, raw


# ─── ForensicEvent converter ──────────────────────────────────────────────────

def to_forensic_events(scan_result: dict) -> list:
    """Convert a process layer result dict into a list of ForensicEvent objects."""
    events = []
    try:
        from api import push_event
        import time
        from shared.schemas import ForensicEvent

        score = scan_result.get("score", 0)
        value = min(score / 10.0, 1.0)
        severity = (
            "critical" if score >= 8 else
            "high"     if score >= 6 else
            "medium"   if score >= 3 else "low"
        )

        for ev_str in scan_result.get("evidence", []):
            signal = "threat_process" if "THREAT" in ev_str else (
                "ai_port"      if "port" in ev_str.lower() else
                "hidden_process" if "Hidden" in ev_str else
                "ai_process"
            )
            event = ForensicEvent(
                timestamp=time.time(),
                source="varchas",
                layer=scan_result.get("layer", "process"),
                signal=signal,
                value=value,
                raw=scan_result.get("raw", {}),
                severity=severity,
                description=ev_str,
            )
            events.append(event)
    except Exception as e:
        print(f"[PROCESS] to_forensic_events error: {e}")
    return events


# ─── Public API ───────────────────────────────────────────────────────────────

def run_process_scan() -> dict:
    """Run all process sub-scanners and return a unified layer result dict."""
    all_evidence: List[str] = []
    raw: Dict[str, Any]     = {}

    proc_score,   proc_ev,   proc_raw   = 0, [], []
    port_score,   port_ev,   port_raw   = 0, [], []
    file_score,   file_ev,   file_raw   = 0, [], []
    threat_score, threat_ev, threat_raw = 0, [], []
    wmi_score,    wmi_ev,    wmi_raw    = 0, [], {}

    try:
        proc_score, proc_ev, proc_raw = _scan_processes()
        all_evidence.extend(proc_ev)
        raw["processes"] = proc_raw
    except Exception as e:
        print(f"[PROCESS] process scan error: {e}")

    try:
        port_score, port_ev, port_raw = _scan_ports()
        all_evidence.extend(port_ev)
        raw["ports"] = port_raw
    except Exception as e:
        print(f"[PROCESS] port scan error: {e}")

    try:
        threat_score, threat_ev, threat_raw = _scan_threat_processes()
        all_evidence.extend(threat_ev)
        raw["threat_hits"] = threat_raw
    except Exception as e:
        print(f"[PROCESS] threat scan error: {e}")

    try:
        wmi_score, wmi_ev, wmi_raw = _scan_wmi_discrepancy()
        all_evidence.extend(wmi_ev)
        raw["wmi_hidden"] = wmi_raw
    except Exception as e:
        print(f"[PROCESS] wmi scan error: {e}")

    try:
        hits = get_model_file_hits()
        for hit in hits:
            file_score = min(file_score + 6, 10)
            file_ev.append(f"Model file accessed: {hit['path']}")
        all_evidence.extend(file_ev)
        raw["model_files"] = hits
    except Exception as e:
        print(f"[PROCESS] model file scan error: {e}")

    final_score = min(
        max(port_score, proc_score, threat_score) + (file_score // 2),
        10
    )
    final_score = min(final_score + wmi_score, 10)

    confidence = 1.0 if caps.can_read_connections else 0.7

    return {
        "layer":      "process",
        "score":      final_score,
        "evidence":   all_evidence,
        "confidence": round(confidence, 2),
        "raw":        raw,
    }
