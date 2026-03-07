"""
layers/process.py — Detects AI tool usage via process names, loaded DLLs,
listening ports, and model file access events.

Three sub-scanners: process/DLL, port listen, and watchdog model-file watcher.
The watchdog watcher is started as a daemon thread at module import time.
"""

import os
import time
import threading
from typing import List, Dict, Any

import psutil  # type: ignore

from config import (
    AI_PROCESS_NAMES, AI_DLLS, AI_PORTS, RAM_SPIKE_MB,
    AI_MODEL_EXTENSIONS, THREAT_PROCESSES,
)
from capability import caps

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

    # watchdog calls these concrete methods; all delegate to dispatch
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

        # Targeted candidate directories — only where AI models actually live
        candidates = [
            # Ollama model store
            os.path.join(os.path.expanduser("~"), ".ollama", "models"),
            # LM Studio model store
            os.path.join(os.path.expanduser("~"), ".cache", "lm-studio", "models"),
            # HuggingFace cache
            os.path.join(os.path.expanduser("~"), ".cache", "huggingface"),
            # Generic "models" folder users commonly create
            os.path.join(os.path.expanduser("~"), "models"),
            os.path.join(os.path.expanduser("~"), "Models"),
            # Windows LM Studio default
            os.path.join(os.path.expanduser("~"), "AppData", "Roaming",
                         "LM Studio", "models"),
            # Temp dirs (model downloads often land here temporarily)
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
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
        print("[PROCESS] Model file watcher started")
    except Exception as e:
        print(f"[PROCESS] Could not start watchdog observer: {e}")


def get_model_file_hits() -> List[Dict[str, Any]]:
    """Return model file access events from the last 60 seconds."""
    cutoff = time.time() - 60.0
    try:
        with _model_hits_lock:
            recent = [h for h in _model_hits if h["timestamp"] >= cutoff]
            # Prune old entries to avoid unbounded growth
            _model_hits[:] = recent
            return list(recent)
    except Exception as e:
        print(f"[PROCESS] get_model_file_hits error: {e}")
        return []


# ─── Sub-scanner 1 — Process name + DLL scan ─────────────────────────────────

def _scan_processes() -> tuple:
    """Scan running processes for AI names, loaded DLLs, and RAM usage.

    Returns (score, evidence, raw_list).
    """
    score    = 0
    evidence: List[str] = []
    raw_procs: List[Dict] = []

    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
            try:
                name    = (proc.info["name"] or "").lower()
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                mem     = proc.info.get("memory_info")
                rss_mb  = mem.rss / (1024 * 1024) if mem else 0

                proc_data: Dict[str, Any] = {
                    "pid":    proc.pid,
                    "name":   proc.info["name"],
                    "rss_mb": round(rss_mb, 1),
                    "flags":  [],
                }

                # Check process name
                name_match = any(ai.lower() in name or ai.lower() in cmdline
                                 for ai in AI_PROCESS_NAMES)
                if name_match:
                    proc_data["flags"].append("AI_PROCESS_NAME")
                    score = min(score + 3, 10)
                    evidence.append(f"AI process '{proc.info['name']}' (PID {proc.pid})")

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
                                    f"AI DLL '{dll}' loaded by '{proc.info['name']}' (PID {proc.pid})"
                                )
                                break
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
                except Exception as e:
                    print(f"[PROCESS] memory_maps error PID {proc.pid}: {e}")

                # RAM spike check
                if rss_mb > RAM_SPIKE_MB:
                    proc_data["flags"].append("RAM_SPIKE")
                    score = min(score + 2, 10)
                    evidence.append(
                        f"RAM spike: '{proc.info['name']}' using {rss_mb:.0f} MB"
                    )

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
    """Check listening TCP ports against AI_PORTS; returns (score, evidence, raw)."""
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
                if port and port in AI_PORTS:
                    service = AI_PORTS[port]
                    score = min(score + 8, 10)
                    evidence.append(f"AI service listening on port {port}: {service}")
                    raw_ports.append({"port": port, "service": service})
            except Exception as e:
                print(f"[PROCESS] port scan inner error: {e}")
    except psutil.AccessDenied:
        print("[PROCESS] AccessDenied on net_connections (port scan)")
    except Exception as e:
        print(f"[PROCESS] port scan error: {e}")

    return score, evidence, raw_ports


# ─── Sub-scanner 3 — Varchas Threat Processes ─────────────────────────────────

def _scan_threat_processes() -> tuple:
    """Scan running processes for blacklisted cheating/tunneling Varchas threats.
    
    Returns (score, evidence, raw_list).
    """
    score    = 0
    evidence: List[str] = []
    raw_list: List[Dict] = []

    try:
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
            try:
                name = (proc.info.get("name") or "").lower()
                exe = (proc.info.get("exe") or "").lower()
                pid = proc.pid
                
                # Check against THREAT_PROCESSES
                for frag, (label, severity) in THREAT_PROCESSES.items():
                    if frag in name or frag in exe:
                        raw_list.append({
                            'pid': pid,
                            'name': proc.info.get("name") or "",
                            'exe': proc.info.get("exe"),
                            'label': label,
                            'severity': severity,
                            'match_key': frag,
                        })
                        
                        if severity == 'critical':
                            score = min(score + 9, 10)
                        elif severity == 'high':
                            score = min(score + 6, 10)
                            
                        evidence.append(f"THREAT: {label} ({severity}) — process '{proc.info.get('name') or ''}' PID {pid}")
                        break # Only trigger once per process
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                print(f"[PROCESS] threat scan inner error: {e}")
                continue
    except Exception as e:
        print(f"[PROCESS] threat scan error: {e}")

    return score, evidence, raw_list


# ─── Sub-scanner 4 — WMI Discrepancy (Windows only) ───────────────────────────

def _scan_wmi_discrepancy() -> tuple:
    """Detect hidden/renamed processes visible to WMI but missed/altered in psutil.
    
    Returns (score, evidence, raw).
    """
    if caps.os_name != "Windows":
        return 0, [], {}

    score    = 0
    evidence: List[str] = []
    raw: Dict[str, Any] = {"hidden": [], "renamed": []}

    try:
        import wmi # type: ignore
        c = wmi.WMI()
        
        # Build psutil map
        psutil_map = {}
        for p in psutil.process_iter(['pid', 'name']):
            psutil_map[p.pid] = p.info.get('name') or ""
            
        # Build wmi map
        wmi_map = {}
        for p in c.Win32_Process():
            try:
                wmi_map[int(p.ProcessId)] = p.Name
            except Exception:
                continue
                
        # Compare
        for pid, wmi_name in wmi_map.items():
            if pid not in psutil_map:
                # Hidden from psutil
                if pid == 0 or pid == 4: # System Idle Process / System
                    continue
                score = min(score + 7, 10)
                evidence.append(f"Hidden/renamed process: WMI='{wmi_name}' PID {pid} not visible to psutil — possible evasion")
                raw["hidden"].append({"pid": pid, "wmi_name": wmi_name})
            else:
                # Name differs significantly
                ps_name = psutil_map[pid]
                if wmi_name and ps_name:
                    wn_lower = wmi_name.lower().strip()
                    pn_lower = ps_name.lower().strip()
                    if len(wn_lower) >= 4 and len(pn_lower) >= 4:
                        if not wn_lower.startswith(pn_lower[:4]) and not pn_lower.startswith(wn_lower[:4]):
                            score = min(score + 7, 10)
                            evidence.append(f"Hidden/renamed process: WMI='{wmi_name}' PID {pid} not visible to psutil — possible evasion")
                            raw["renamed"].append({"pid": pid, "wmi_name": wmi_name, "ps_name": ps_name})
                            
    except ImportError:
        pass # WMI not available, ignore
    except Exception as e:
        print(f"[PROCESS] WMI discrepancy scan error: {e}")
        raw["error"] = str(e)

    return score, evidence, raw


# ─── Public API ───────────────────────────────────────────────────────────────

def run_process_scan() -> dict:
    """Run all process sub-scanners and return a unified layer result dict."""
    all_evidence: List[str] = []
    raw: Dict[str, Any]     = {}

    proc_score, proc_ev, proc_raw = 0, [], []
    port_score, port_ev, port_raw = 0, [], []
    file_score, file_ev, file_raw = 0, [], []
    threat_score, threat_ev, threat_raw = 0, [], []
    wmi_score, wmi_ev, wmi_raw = 0, [], {}

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

    # Combine: port / threat score is high-confidence, take the maximum and add partials
    final_score = min(
        max(port_score, proc_score, threat_score) + (file_score // 2),
        10
    )
    final_score = min(final_score + wmi_score, 10)

    # Confidence is slightly reduced without connection access
    confidence = 1.0 if caps.can_read_connections else 0.7

    return {
        "layer":      "process",
        "score":      final_score,
        "evidence":   all_evidence,
        "confidence": round(confidence, 2),
        "raw":        raw,
    }
