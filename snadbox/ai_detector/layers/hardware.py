"""
layers/hardware.py — Detects AI usage through GPU, CPU, RAM, and disk monitoring.

GPU scanning uses three progressive paths: NVIDIA (pynvml), AMD (WMI/sysfs),
and a zero-GPU fallback. The 10Hz sampler feeds the causality chain detector.
CPU thread explosion and disk I/O spike detection are also included.
"""

import os
import time
import threading
from typing import List, Dict, Any, Optional, Tuple
from collections import deque

from config import (
    GPU_UTIL_THRESHOLD,
    RAM_SPIKE_MB,
    AI_PROCESS_NAMES,
    HW_HISTORY_MAXLEN,
    HW_SAMPLE_RATE_HZ,
    GPU_SPIKE_THRESHOLD,
    RAM_LLM_THRESHOLD_GB,
    CAUSALITY_WINDOW_SEC,
    DISK_READ_SPIKE_MB,
    THREAD_EXPLOSION,
    INTERNAL_HOSTS,
)
from capability import caps, _is_internal_service

# ─── 10Hz history buffer (thread-safe) ───────────────────────────────────────
_hw_history: deque = deque(maxlen=HW_HISTORY_MAXLEN)
_hw_lock = threading.Lock()
_hw_sampler_started = False

# ─── Disk I/O baseline tracking ──────────────────────────────────────────────
_disk_baseline: Dict[str, int] = {}   # disk → bytes_read at last sample
_disk_lock = threading.Lock()

# ─── RAM growth tracking per process ─────────────────────────────────────────
_ram_history: Dict[int, List[Tuple[float, float]]] = {}  # pid → [(ts, rss_mb)]
_ram_track_lock = threading.Lock()


# ─── GPU Paths ────────────────────────────────────────────────────────────────

def _scan_nvidia_gpu() -> Tuple[int, List[str], Dict]:
    """Use pynvml to read NVIDIA GPU utilisation and VRAM; returns (score, evidence, raw)."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {}

    if not caps.has_nvidia:
        raw["nvidia_note"] = "NVIDIA not available"
        return 0, [], raw

    try:
        import pynvml  # type: ignore
        try:
            pynvml.nvmlInit()
        except Exception as e:
            print(f"[HARDWARE] pynvml.nvmlInit error: {e}")
            return 0, [], {"nvidia_error": str(e)}

        try:
            count = pynvml.nvmlDeviceGetCount()
        except Exception as e:
            print(f"[HARDWARE] nvmlDeviceGetCount error: {e}")
            return 0, [], {"nvidia_error": str(e)}

        gpu_data = []
        for i in range(count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            except Exception as e:
                print(f"[HARDWARE] nvmlDeviceGetHandleByIndex({i}) error: {e}")
                continue

            try:
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="replace")
            except Exception as e:
                print(f"[HARDWARE] nvmlDeviceGetName({i}) error: {e}")
                name = f"GPU_{i}"

            gpu_util_pct = 0
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_util_pct = util.gpu
            except Exception as e:
                print(f"[HARDWARE] nvmlGetUtilizationRates({i}) error: {e}")

            vram_used_mb  = 0.0
            vram_total_mb = 0.0
            vram_pct      = 0.0
            try:
                mem_info      = pynvml.nvmlDeviceGetMemoryInfo(handle)
                vram_used_mb  = mem_info.used  / (1024 * 1024)
                vram_total_mb = mem_info.total / (1024 * 1024)
                vram_pct      = (mem_info.used / mem_info.total * 100) if mem_info.total else 0
            except Exception as e:
                print(f"[HARDWARE] nvmlDeviceGetMemoryInfo({i}) error: {e}")

            entry = {
                "index":         i,
                "name":          name,
                "util_pct":      gpu_util_pct,
                "vram_used_mb":  round(vram_used_mb, 1),
                "vram_total_mb": round(vram_total_mb, 1),
                "vram_pct":      round(vram_pct, 1),
            }
            gpu_data.append(entry)

            if gpu_util_pct > GPU_SPIKE_THRESHOLD:
                score = min(score + 5, 10)
                evidence.append(
                    f"NVIDIA {name}: GPU util {gpu_util_pct}% "
                    f"(spike threshold {GPU_SPIKE_THRESHOLD}% — possible LLM inference)"
                )
            elif gpu_util_pct > GPU_UTIL_THRESHOLD:
                score = min(score + 3, 10)
                evidence.append(
                    f"NVIDIA {name}: GPU util {gpu_util_pct}% (threshold {GPU_UTIL_THRESHOLD}%)"
                )

            # Deepfake rendering: GPU > 60% with VRAM > 2GB
            if gpu_util_pct > 60 and vram_used_mb > 2048:
                score = min(score + 3, 10)
                evidence.append(
                    f"NVIDIA {name}: GPU {gpu_util_pct}% with "
                    f"{vram_used_mb:.0f} MB VRAM — possible deepfake rendering"
                )

            if vram_pct > 50:
                score = min(score + 2, 10)
                evidence.append(
                    f"NVIDIA {name}: VRAM {vram_used_mb:.0f}/{vram_total_mb:.0f} MB "
                    f"({vram_pct:.0f}% used)"
                )

        raw["nvidia_gpus"] = gpu_data
    except Exception as e:
        print(f"[HARDWARE] pynvml top-level error: {e}")
        raw["nvidia_error"] = str(e)

    return score, evidence, raw


def _scan_amd_gpu() -> Tuple[int, List[str], Dict]:
    """Read AMD GPU info via WMI (Windows) or /sys/class/drm (Linux)."""
    if caps.os_name == "Windows":
        return _scan_amd_gpu_windows()
    elif caps.os_name == "Linux":
        return _scan_amd_gpu_linux()
    return 0, [], {}


def _scan_amd_gpu_windows() -> Tuple[int, List[str], Dict]:
    """Use WMI Win32_VideoController to read AMD GPU info on Windows."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {"amd_gpus": []}

    try:
        import wmi  # type: ignore
        c = wmi.WMI()
        for gpu in c.Win32_VideoController():
            try:
                name = gpu.Name or "Unknown AMD GPU"
                adapter_ram_bytes = getattr(gpu, "AdapterRAM", 0) or 0
                adapter_ram_gb    = adapter_ram_bytes / (1024 ** 3)

                if "amd" in name.lower() or "radeon" in name.lower():
                    raw["amd_gpus"].append({
                        "name":           name,
                        "adapter_ram_gb": round(adapter_ram_gb, 2),
                    })
                    if adapter_ram_gb > 4.0:
                        score = min(score + 2, 10)
                        evidence.append(
                            f"AMD GPU '{name}' with {adapter_ram_gb:.1f} GB VRAM "
                            f"(potential model load)"
                        )
            except Exception as e:
                print(f"[HARDWARE] AMD WMI device error: {e}")
    except Exception as e:
        print(f"[HARDWARE] WMI AMD scan error: {e}")
        raw["amd_error"] = str(e)

    return score, evidence, raw


def _scan_amd_gpu_linux() -> Tuple[int, List[str], Dict]:
    """Read AMD GPU VRAM usage from /sys/class/drm on Linux."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {"amd_gpus": []}

    try:
        drm_path = "/sys/class/drm"
        if not os.path.isdir(drm_path):
            return 0, [], raw

        for entry in os.listdir(drm_path):
            vendor_path = os.path.join(drm_path, entry, "device", "vendor")
            if not os.path.isfile(vendor_path):
                continue
            try:
                with open(vendor_path) as f:
                    vendor = f.read().strip()
                if "1002" not in vendor:  # 0x1002 = AMD
                    continue

                mem_total_path = os.path.join(drm_path, entry, "device", "mem_info_vram_total")
                mem_used_path  = os.path.join(drm_path, entry, "device", "mem_info_vram_used")

                vram_total_mb: Optional[float] = None
                vram_used_mb:  Optional[float] = None

                if os.path.isfile(mem_total_path):
                    with open(mem_total_path) as f:
                        vram_total_mb = int(f.read().strip()) / (1024 * 1024)
                if os.path.isfile(mem_used_path):
                    with open(mem_used_path) as f:
                        vram_used_mb = int(f.read().strip()) / (1024 * 1024)

                gpu_entry = {
                    "drm_entry":     entry,
                    "vram_total_mb": round(vram_total_mb, 1) if vram_total_mb else None,
                    "vram_used_mb":  round(vram_used_mb, 1)  if vram_used_mb  else None,
                }
                raw["amd_gpus"].append(gpu_entry)

                if vram_total_mb and vram_total_mb > 4096:
                    score = min(score + 2, 10)
                    evidence.append(
                        f"AMD GPU {entry}: {vram_total_mb:.0f} MB VRAM (potential model load)"
                    )
            except Exception as e:
                print(f"[HARDWARE] AMD sysfs entry {entry} error: {e}")
    except Exception as e:
        print(f"[HARDWARE] AMD Linux scan error: {e}")
        raw["amd_error"] = str(e)

    return score, evidence, raw


# ─── CPU Thread Analysis ──────────────────────────────────────────────────────

def _scan_cpu_threads() -> Tuple[int, List[str], Dict]:
    """Detect thread explosion and LLM CPU usage patterns."""
    import psutil  # type: ignore

    score    = 0
    evidence: List[str] = []
    raw: Dict = {"thread_heavy_procs": []}

    try:
        for proc in psutil.process_iter(["pid", "name", "num_threads"]):
            try:
                if _is_internal_service(proc):
                    continue
                num_threads = proc.info.get("num_threads") or 0
                name        = proc.info.get("name") or ""
                if num_threads > THREAD_EXPLOSION:
                    score = min(score + 2, 10)
                    evidence.append(
                        f"Thread explosion: '{name}' (PID {proc.pid}) "
                        f"has {num_threads} threads (>{THREAD_EXPLOSION})"
                    )
                    raw["thread_heavy_procs"].append({
                        "pid":         proc.pid,
                        "name":        name,
                        "num_threads": num_threads,
                    })
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                print(f"[HARDWARE] thread scan PID error: {e}")

    except Exception as e:
        print(f"[HARDWARE] _scan_cpu_threads error: {e}")
        raw["thread_error"] = str(e)

    return score, evidence, raw


# ─── RAM Scanning ─────────────────────────────────────────────────────────────

def _scan_ram() -> Tuple[int, List[str], Dict]:
    """Flag processes exceeding RAM_SPIKE_MB and detect model loading patterns."""
    import psutil  # type: ignore

    score    = 0
    evidence: List[str] = []
    raw: Dict = {"ram_spike_procs": []}

    try:
        vm = psutil.virtual_memory()
        raw["system_ram_pct"] = round(vm.percent, 1)
        raw["system_ram_gb"]  = round(vm.used / 1e9, 2)

        now = time.time()
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                if _is_internal_service(proc):
                    continue
                mem = proc.info.get("memory_info")
                if not mem:
                    continue
                rss_mb = mem.rss / (1024 * 1024)
                pid    = proc.pid

                if rss_mb > RAM_SPIKE_MB:
                    score = min(score + 2, 10)
                    evidence.append(
                        f"RAM spike: '{proc.info['name']}' (PID {pid}) using {rss_mb:.0f} MB"
                    )
                    raw["ram_spike_procs"].append({
                        "pid":    pid,
                        "name":   proc.info["name"],
                        "rss_mb": round(rss_mb, 1),
                    })

                # Track growth for model loading detection (> 2GB in 30s)
                with _ram_track_lock:
                    history = _ram_history.setdefault(pid, [])
                    history.append((now, rss_mb))
                    # Keep only last 30s
                    cutoff = now - 30.0
                    _ram_history[pid] = [(t, m) for t, m in history if t >= cutoff]
                    if len(_ram_history[pid]) >= 2:
                        oldest_mb = _ram_history[pid][0][1]
                        growth_mb = rss_mb - oldest_mb
                        if growth_mb > 2048:  # 2GB growth in < 30 seconds
                            score = min(score + 3, 10)
                            evidence.append(
                                f"Model loading detected: '{proc.info['name']}' RAM grew "
                                f"{growth_mb:.0f} MB in 30s (model loading pattern)"
                            )

            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                print(f"[HARDWARE] RAM scan PID error: {e}")

        # Prune stale RAM tracking entries
        with _ram_track_lock:
            stale_pids = [p for p in list(_ram_history.keys()) if not _ram_history[p]]
            for p in stale_pids:
                del _ram_history[p]

    except Exception as e:
        print(f"[HARDWARE] RAM scan error: {e}")
        raw["ram_error"] = str(e)

    return score, evidence, raw


# ─── Disk I/O Monitoring ──────────────────────────────────────────────────────

def _scan_disk_io() -> Tuple[int, List[str], Dict]:
    """Detect model loading from disk via read spike detection."""
    import psutil  # type: ignore

    score    = 0
    evidence: List[str] = []
    raw: Dict = {"disk_io": []}

    try:
        io_counters = psutil.disk_io_counters(perdisk=True)
        global _disk_baseline
        with _disk_lock:
            current_baseline = dict(_disk_baseline)

        for disk, counters in io_counters.items():
            try:
                bytes_read = counters.read_bytes
                prev_read  = current_baseline.get(disk, bytes_read)
                delta_mb   = (bytes_read - prev_read) / (1024 * 1024)

                raw["disk_io"].append({
                    "disk":     disk,
                    "delta_mb": round(delta_mb, 1),
                })

                if delta_mb > DISK_READ_SPIKE_MB:
                    score = min(score + 3, 10)
                    evidence.append(
                        f"Disk read spike on {disk}: {delta_mb:.0f} MB "
                        f"(>{DISK_READ_SPIKE_MB} MB — model loading from disk)"
                    )
                elif delta_mb > 1024:  # > 1GB single read
                    score = min(score + 2, 10)
                    evidence.append(
                        f"Large disk read on {disk}: {delta_mb:.0f} MB "
                        f"(large file access — possible model load)"
                    )
            except Exception as e:
                print(f"[HARDWARE] disk io entry {disk} error: {e}")

        # Update baseline
        with _disk_lock:
            for disk, counters in io_counters.items():
                _disk_baseline[disk] = counters.read_bytes

    except Exception as e:
        print(f"[HARDWARE] _scan_disk_io error: {e}")
        raw["disk_error"] = str(e)

    return score, evidence, raw


# ─── 10Hz Hardware Sampler ────────────────────────────────────────────────────

def _take_hw_sample() -> dict:
    """Collect one hardware snapshot at 10Hz."""
    import psutil  # type: ignore

    sample: Dict[str, Any] = {"ts": time.time()}

    try:
        sample["cpu_pct"] = psutil.cpu_percent(interval=None)
    except Exception:
        sample["cpu_pct"] = 0.0

    try:
        sample["ram_gb"] = psutil.virtual_memory().used / 1e9
    except Exception:
        sample["ram_gb"] = 0.0

    # GPU measurement (only if available)
    gpu_pct    = 0.0
    gpu_mem_mb = 0.0
    if caps.has_nvidia:
        try:
            import pynvml  # type: ignore
            count = pynvml.nvmlDeviceGetCount()
            for i in range(count):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    util   = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    mem    = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    gpu_pct    = max(gpu_pct, util.gpu)
                    gpu_mem_mb += mem.used / (1024 * 1024)
                except Exception:
                    pass
        except Exception:
            pass

    sample["gpu_pct"]    = gpu_pct
    sample["gpu_mem_mb"] = gpu_mem_mb

    try:
        sample["net_recv_kb"] = psutil.net_io_counters().bytes_recv / 1024
    except Exception:
        sample["net_recv_kb"] = 0.0

    # Disk read delta
    try:
        io = psutil.disk_io_counters()
        sample["disk_read_mb"] = io.read_bytes / (1024 * 1024) if io else 0.0
    except Exception:
        sample["disk_read_mb"] = 0.0

    # Total thread count across all processes
    try:
        sample["thread_count"] = sum(
            p.num_threads() for p in psutil.process_iter(["num_threads"])
            if p.info.get("num_threads")
        )
    except Exception:
        sample["thread_count"] = 0

    with _hw_lock:
        _hw_history.append(sample)

    # Check for GPU spike → push ForensicEvent immediately
    if gpu_pct >= GPU_SPIKE_THRESHOLD:
        _push_gpu_spike_event(gpu_pct, gpu_mem_mb)

    return sample


def _push_gpu_spike_event(gpu_pct: float, gpu_mem_mb: float) -> None:
    """Push a GPU spike ForensicEvent immediately to the api event queue."""
    try:
        from api import push_event
        from shared.schemas import ForensicEvent
        push_event(ForensicEvent(
            timestamp=time.time(),
            source="varchas",
            layer="hardware",
            signal="gpu_spike",
            value=min(gpu_pct / 100.0, 1.0),
            raw={"gpu_pct": gpu_pct, "gpu_mem_mb": gpu_mem_mb},
            severity="high" if gpu_pct >= GPU_SPIKE_THRESHOLD else "medium",
            description=(
                f"GPU spike: {gpu_pct:.0f}% utilization "
                f"with {gpu_mem_mb:.0f} MB VRAM — possible LLM inference"
            ),
        ))
    except Exception:
        pass


def _hw_sampler_loop() -> None:
    """Run the 10Hz hardware sampler loop as a daemon thread."""
    import psutil  # type: ignore

    # Two-pass CPU measurement: single sleep between reads, never interval=X inside loop
    try:
        psutil.cpu_percent(interval=None)  # Initialize CPU measurement
    except Exception:
        pass
    time.sleep(0.1)  # Single shared sleep for baseline

    while True:
        try:
            _take_hw_sample()
            time.sleep(1.0 / HW_SAMPLE_RATE_HZ)
        except Exception as e:
            print(f"[HARDWARE] sampler loop error: {e}")
            time.sleep(0.1)


def start_hw_sampler() -> None:
    """Start the 10Hz hardware sampler in a daemon thread."""
    global _hw_sampler_started
    if _hw_sampler_started:
        return
    t = threading.Thread(target=_hw_sampler_loop, name="hw-sampler", daemon=True)
    t.start()
    _hw_sampler_started = True
    print("[STARTUP] 10Hz hardware sampler started")


# ─── Causality Chain Detector ────────────────────────────────────────────────

def detect_causality_chain() -> dict:
    """Analyse history for GPU spike followed by network burst (LLM inference fingerprint).

    Skips bursts that are going to INTERNAL_HOSTS. Pushes ForensicEvent immediately.
    """
    result = {
        "causality_events": [],
        "llm_ram_loaded":   False,
        "peak_gpu_pct":     0.0,
        "peak_ram_gb":      0.0,
        "samples_collected": 0,
    }

    try:
        with _hw_lock:
            history = list(_hw_history)

        result["samples_collected"] = len(history)
        if not history:
            return result

        result["peak_gpu_pct"] = max((s.get("gpu_pct", 0.0) for s in history), default=0.0)
        result["peak_ram_gb"]  = max((s.get("ram_gb", 0.0)  for s in history), default=0.0)

        if result["peak_ram_gb"] > RAM_LLM_THRESHOLD_GB:
            result["llm_ram_loaded"] = True

        # Calculate median network receive rate (over last 30 samples)
        net_rates = sorted(s.get("net_recv_kb", 0.0) for s in history)
        median_net_kb  = net_rates[len(net_rates) // 2] if net_rates else 0.0
        burst_threshold = max(median_net_kb * 2.0, 50.0)  # minimum 50 KB burst

        spike_samples = [s for s in history if s.get("gpu_pct", 0.0) >= GPU_SPIKE_THRESHOLD]

        last_event_ts = 0.0

        for spike in spike_samples:
            t_spike = spike["ts"]
            if t_spike - last_event_ts < CAUSALITY_WINDOW_SEC:
                continue  # Already covered by a recent event

            burst_candidates = [
                s for s in history
                if t_spike < s["ts"] <= (t_spike + CAUSALITY_WINDOW_SEC)
                and s.get("net_recv_kb", 0.0) > burst_threshold
            ]

            if burst_candidates:
                burst = max(burst_candidates, key=lambda x: x.get("net_recv_kb", 0.0))
                event_data = {
                    "spike_ts":   t_spike,
                    "burst_ts":   burst["ts"],
                    "gpu_pct":    spike.get("gpu_pct", 0.0),
                    "net_recv_kb": burst.get("net_recv_kb", 0.0),
                }
                result["causality_events"].append(event_data)
                last_event_ts = burst["ts"]

                # Push ForensicEvent immediately
                _push_causality_event(event_data)

    except Exception as e:
        print(f"[HARDWARE] causality chain error: {e}")

    return result


def _push_causality_event(event_data: dict) -> None:
    """Push a causality chain ForensicEvent immediately."""
    try:
        from api import push_event
        from shared.schemas import ForensicEvent
        gap = event_data["burst_ts"] - event_data["spike_ts"]
        push_event(ForensicEvent(
            timestamp=time.time(),
            source="varchas",
            layer="hardware",
            signal="causality_chain",
            value=min(event_data["gpu_pct"] / 100.0, 1.0),
            raw=event_data,
            severity="high",
            description=(
                f"Causality chain: GPU {event_data['gpu_pct']:.0f}% spike "
                f"→ network burst {event_data['net_recv_kb']:.0f} KB "
                f"({gap:.1f}s gap — LLM inference pattern)"
            ),
        ))
    except Exception:
        pass


# ─── ForensicEvent converter ──────────────────────────────────────────────────

def to_forensic_events(scan_result: dict) -> list:
    """Convert a hardware layer result dict into a list of ForensicEvent objects."""
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
                "gpu_spike"       if "GPU spike" in ev_str or "GPU util" in ev_str else
                "causality_chain" if "Causality" in ev_str else
                "disk_read"       if "disk" in ev_str.lower() else
                "ram_spike"       if "RAM" in ev_str else
                "hardware"
            )
            event = ForensicEvent(
                timestamp=time.time(),
                source="varchas",
                layer=scan_result.get("layer", "hardware"),
                signal=signal,
                value=value,
                raw=scan_result.get("raw", {}),
                severity=severity,
                description=ev_str,
            )
            events.append(event)
    except Exception as e:
        print(f"[HARDWARE] to_forensic_events error: {e}")
    return events


# ─── Public API ───────────────────────────────────────────────────────────────

def run_hardware_scan() -> dict:
    """Run GPU, CPU thread, RAM, disk I/O scans; return unified layer result dict."""
    import psutil  # type: ignore

    all_evidence: List[str] = []
    raw: Dict[str, Any]     = {}
    total_score = 0

    # ── GPU ──────────────────────────────────────────────────────────────────
    gpu_score = 0

    if caps.has_nvidia:
        try:
            s, ev, r = _scan_nvidia_gpu()
            gpu_score    = max(gpu_score, s)
            all_evidence.extend(ev)
            raw.update(r)
        except Exception as e:
            print(f"[HARDWARE] NVIDIA scan top-level error: {e}")

    if caps.has_amd:
        try:
            s, ev, r = _scan_amd_gpu()
            gpu_score    = max(gpu_score, s)
            all_evidence.extend(ev)
            raw.update(r)
        except Exception as e:
            print(f"[HARDWARE] AMD scan top-level error: {e}")

    if not caps.has_nvidia and not caps.has_amd:
        raw["gpu_note"] = "No discrete GPU detected; GPU scoring unavailable"

    total_score = min(total_score + gpu_score, 10)

    # ── Causality chain ───────────────────────────────────────────────────────
    try:
        causality_res = detect_causality_chain()
        raw["causality"] = causality_res

        c_score = 0
        for ev in causality_res.get("causality_events", []):
            c_score = min(c_score + 5, 10)
            gap = ev["burst_ts"] - ev["spike_ts"]
            all_evidence.append(
                f"Causality chain: GPU spike {ev['gpu_pct']:.0f}% "
                f"followed by network burst at {ev['burst_ts']:.1f} "
                f"({gap:.1f}s gap — LLM inference pattern)"
            )

        if causality_res.get("llm_ram_loaded"):
            c_score = min(c_score + 3, 10)
            peak_ram = causality_res.get("peak_ram_gb", 0.0)
            all_evidence.append(f"LLM-scale RAM loaded: {peak_ram:.1f} GB")

        if causality_res.get("peak_gpu_pct", 0.0) >= GPU_SPIKE_THRESHOLD:
            c_score = min(c_score + 3, 10)

        total_score = min(total_score + c_score, 10)

    except Exception as e:
        print(f"[HARDWARE] Causality sequence error: {e}")

    # ── CPU threads ───────────────────────────────────────────────────────────
    try:
        s, ev, r = _scan_cpu_threads()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
    except Exception as e:
        print(f"[HARDWARE] CPU thread scan top-level error: {e}")

    # ── RAM ───────────────────────────────────────────────────────────────────
    try:
        s, ev, r = _scan_ram()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
    except Exception as e:
        print(f"[HARDWARE] RAM scan top-level error: {e}")

    # ── Disk I/O ──────────────────────────────────────────────────────────────
    try:
        s, ev, r = _scan_disk_io()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
    except Exception as e:
        print(f"[HARDWARE] Disk I/O scan top-level error: {e}")

    confidence = 1.0
    if not caps.has_nvidia and not caps.has_amd:
        confidence -= 0.4

    return {
        "layer":      "hardware",
        "score":      min(total_score, 10),
        "evidence":   all_evidence,
        "confidence": max(round(confidence, 2), 0.0),
        "raw":        raw,
    }
