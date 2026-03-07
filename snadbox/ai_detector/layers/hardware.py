"""
layers/hardware.py — Detects AI usage through GPU, CPU, and RAM monitoring.

GPU scanning uses three progressive paths: NVIDIA (pynvml), AMD (WMI/sysfs),
and a zero-GPU fallback. CPU and RAM scanning use psutil.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import threading
import time

from config import (
    GPU_UTIL_THRESHOLD,
    RAM_SPIKE_MB,
    AI_PROCESS_NAMES,
    HW_HISTORY_MAXLEN,
    HW_SAMPLE_RATE_HZ,
    GPU_SPIKE_THRESHOLD,
    RAM_LLM_THRESHOLD_GB,
    CAUSALITY_WINDOW_SEC,
)
from capability import caps

# 10Hz history buffer — thread-safe
_hw_history: deque = deque(maxlen=HW_HISTORY_MAXLEN)
_hw_lock = threading.Lock()
_hw_sampler_started = False


# ─── GPU Paths ────────────────────────────────────────────────────────────────

def _scan_nvidia_gpu() -> Tuple[int, List[str], Dict]:
    """Use pynvml to read NVIDIA GPU utilisation and VRAM; returns (score, evidence, raw)."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {}

    try:
        import pynvml  # type: ignore
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        gpu_data = []

        for i in range(count):
            try:
                handle  = pynvml.nvmlDeviceGetHandleByIndex(i)
                name    = pynvml.nvmlDeviceGetName(handle)
                # Decode if bytes
                if isinstance(name, bytes):
                    name = name.decode("utf-8", errors="replace")
                util    = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)

                gpu_util_pct = util.gpu
                vram_used_mb = mem_info.used  / (1024 * 1024)
                vram_total_mb= mem_info.total / (1024 * 1024)
                vram_pct     = (mem_info.used / mem_info.total * 100) if mem_info.total else 0

                entry = {
                    "index":        i,
                    "name":         name,
                    "util_pct":     gpu_util_pct,
                    "vram_used_mb": round(vram_used_mb, 1),
                    "vram_total_mb":round(vram_total_mb, 1),
                    "vram_pct":     round(vram_pct, 1),
                }
                gpu_data.append(entry)

                if gpu_util_pct > GPU_UTIL_THRESHOLD:
                    score = min(score + 3, 10)
                    evidence.append(
                        f"NVIDIA {name}: GPU util {gpu_util_pct}% (threshold {GPU_UTIL_THRESHOLD}%)"
                    )

                if vram_pct > 50:
                    score = min(score + 2, 10)
                    evidence.append(
                        f"NVIDIA {name}: VRAM {vram_used_mb:.0f}/{vram_total_mb:.0f} MB "
                        f"({vram_pct:.0f}% used)"
                    )
            except Exception as e:
                print(f"[HARDWARE] NVIDIA device {i} error: {e}")

        raw["nvidia_gpus"] = gpu_data
    except Exception as e:
        print(f"[HARDWARE] pynvml error: {e}")
        raw["nvidia_error"] = str(e)

    return score, evidence, raw


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

                entry = {
                    "name":           name,
                    "adapter_ram_gb": round(adapter_ram_gb, 2),
                }

                if ("amd" in name.lower() or "radeon" in name.lower()):
                    raw["amd_gpus"].append(entry)
                    # > 4 GB VRAM could indicate a model is loaded
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
                    "drm_entry":    entry,
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


# ─── 10Hz Hardware Sampler & Causality Chain ──────────────────────────────────

def _take_hw_sample() -> dict:
    """Collect one hardware snapshot. Returns dict with ts, cpu_pct, ram_gb, gpu_pct, gpu_mem_mb, net_recv_kb."""
    import psutil # type: ignore
    
    sample = {"ts": time.time()}
    
    try:
        sample["cpu_pct"] = psutil.cpu_percent(interval=None)
    except Exception:
        sample["cpu_pct"] = 0.0
        
    try:
        sample["ram_gb"] = psutil.virtual_memory().used / 1e9
    except Exception:
        sample["ram_gb"] = 0.0
        
    gpu_pct = 0.0
    gpu_mem_mb = 0.0
    if caps.has_nvidia:
        try:
            import pynvml # type: ignore
            # Get max util and total used memory across all NVIDIA GPUs
            count = pynvml.nvmlDeviceGetCount()
            for i in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_pct = max(gpu_pct, util.gpu)
                gpu_mem_mb += mem.used / (1024 * 1024)
        except Exception:
            pass
            
    sample["gpu_pct"] = gpu_pct
    sample["gpu_mem_mb"] = gpu_mem_mb
    
    try:
        sample["net_recv_kb"] = psutil.net_io_counters().bytes_recv / 1024
    except Exception:
        sample["net_recv_kb"] = 0.0
        
    with _hw_lock:
        _hw_history.append(sample)
        
    return sample


def _hw_sampler_loop() -> None:
    import psutil # type: ignore
    try:
        psutil.cpu_percent(interval=None) # Initialize
    except Exception:
        pass
    time.sleep(0.1)
    
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
    print("[HARDWARE] 10Hz hardware sampler started")


def detect_causality_chain() -> dict:
    """Analyze history for GPU spike followed by network burst, or LLM-scale RAM usage."""
    result = {
        'causality_events': [],
        'llm_ram_loaded': False,
        'peak_gpu_pct': 0.0,
        'peak_ram_gb': 0.0,
        'samples_collected': 0,
    }
    
    try:
        with _hw_lock:
            history = list(_hw_history)
            
        result['samples_collected'] = len(history)
        if not history:
            return result
            
        result['peak_gpu_pct'] = max((s.get('gpu_pct', 0.0) for s in history), default=0.0)
        result['peak_ram_gb'] = max((s.get('ram_gb', 0.0) for s in history), default=0.0)
        
        if result['peak_ram_gb'] > RAM_LLM_THRESHOLD_GB:
            result['llm_ram_loaded'] = True
            
        # Calculate median network receive rate
        net_rates = sorted(s.get('net_recv_kb', 0.0) for s in history)
        median_net_kb = net_rates[len(net_rates)//2] if net_rates else 0.0
        burst_threshold = max(median_net_kb * 2.0, 50.0) # minimum 50 KB burst
        
        spike_samples = [s for s in history if s.get('gpu_pct', 0.0) >= GPU_SPIKE_THRESHOLD]
        
        # Don't double-count events close in time
        last_event_ts = 0.0
        
        for spike in spike_samples:
            t_spike = spike['ts']
            if t_spike - last_event_ts < CAUSALITY_WINDOW_SEC:
                continue # Already covered 
                
            # Find subsequent network burst
            burst_candidates = [s for s in history 
                              if t_spike < s['ts'] <= (t_spike + CAUSALITY_WINDOW_SEC) 
                              and s.get('net_recv_kb', 0.0) > burst_threshold]
                              
            if burst_candidates:
                burst = max(burst_candidates, key=lambda x: x.get('net_recv_kb', 0.0))
                result['causality_events'].append({
                    'spike_ts': t_spike,
                    'burst_ts': burst['ts'],
                    'gpu_pct': spike.get('gpu_pct', 0.0),
                    'net_recv_kb': burst.get('net_recv_kb', 0.0)
                })
                last_event_ts = burst['ts']
                
    except Exception as e:
        print(f"[HARDWARE] causality chain error: {e}")
        
    return result


# ─── CPU Scanning (Fallback) ──────────────────────────────────────────────────

def _scan_cpu() -> Tuple[int, List[str], Dict]:
    """[FALLBACK] Flag top CPU consumers and match against AI_PROCESS_NAMES."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {"high_cpu_procs": []}

    try:
        import psutil  # type: ignore
        import time

        # Pass 1 — initiate measurement on all processes simultaneously
        procs = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc.cpu_percent(interval=None)
                procs.append(proc)
            except (psutil.NoSuchProcess, psutil.ZombieProcess,
                    psutil.AccessDenied):
                continue
            except Exception:
                continue

        # Single shared sleep — measures all processes simultaneously
        time.sleep(0.5)

        # Pass 2 — read results
        top_procs = []
        for proc in procs:
            try:
                cpu = proc.cpu_percent(interval=None)
                if cpu > 20.0:
                    top_procs.append({
                        "pid":     proc.pid,
                        "name":    proc.info.get("name") or "",
                        "cpu_pct": cpu,
                    })
            except (psutil.NoSuchProcess, psutil.ZombieProcess,
                    psutil.AccessDenied):
                continue
            except Exception as e:
                print(f"[HARDWARE] cpu_percent pass2 PID {proc.pid}: {e}")

        # Sort by CPU usage descending, keep top 5
        top_procs.sort(key=lambda p: p["cpu_pct"], reverse=True)
        top_procs = top_procs[:5]
        raw["high_cpu_procs"] = top_procs

        for p in top_procs:
            name_lower = p["name"].lower()
            if any(ai.lower() in name_lower for ai in AI_PROCESS_NAMES):
                score = min(score + 3, 10)
                evidence.append(
                    f"AI process '{p['name']}' consuming {p['cpu_pct']:.1f}% CPU"
                )
    except Exception as e:
        print(f"[HARDWARE] CPU scan error: {e}")
        raw["cpu_error"] = str(e)

    return score, evidence, raw


# ─── RAM Scanning ─────────────────────────────────────────────────────────────

def _scan_ram() -> Tuple[int, List[str], Dict]:
    """Flag processes exceeding RAM_SPIKE_MB; return (score, evidence, raw)."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {"ram_spike_procs": []}

    try:
        import psutil  # type: ignore

        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                mem = proc.info.get("memory_info")
                if not mem:
                    continue
                rss_mb = mem.rss / (1024 * 1024)
                if rss_mb > RAM_SPIKE_MB:
                    score = min(score + 2, 10)
                    evidence.append(
                        f"RAM spike: '{proc.info['name']}' (PID {proc.pid}) using {rss_mb:.0f} MB"
                    )
                    raw["ram_spike_procs"].append({
                        "pid":    proc.pid,
                        "name":   proc.info["name"],
                        "rss_mb": round(rss_mb, 1),
                    })
                    if score >= 4:  # cap accumulation
                        break
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                print(f"[HARDWARE] RAM scan PID error: {e}")
    except Exception as e:
        print(f"[HARDWARE] RAM scan error: {e}")
        raw["ram_error"] = str(e)

    return score, evidence, raw


# ─── Public API ───────────────────────────────────────────────────────────────

def run_hardware_scan() -> dict:
    """Run GPU, CPU, and RAM scans; return unified layer result dict."""
    all_evidence: List[str] = []
    raw: Dict[str, Any]     = {}
    total_score = 0

    # ── GPU ─────────────────────────────────────────────────────────────
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
            if caps.os_name == "Windows":
                s, ev, r = _scan_amd_gpu_windows()
            else:
                s, ev, r = _scan_amd_gpu_linux()
            gpu_score    = max(gpu_score, s)
            all_evidence.extend(ev)
            raw.update(r)
        except Exception as e:
            print(f"[HARDWARE] AMD scan top-level error: {e}")

    if not caps.has_nvidia and not caps.has_amd:
        raw["gpu_note"] = "No discrete GPU detected; GPU scoring unavailable"

    total_score = min(total_score + gpu_score, 10)

    # ── CPU / Causality ──────────────────────────────────────────────────
    try:
        causality_res = detect_causality_chain()
        raw["causality"] = causality_res
        
        c_score = 0
        for ev in causality_res.get('causality_events', []):
            c_score = min(c_score + 5, 10)
            gap = ev['burst_ts'] - ev['spike_ts']
            all_evidence.append(
                f"Causality chain: GPU spike {ev['gpu_pct']:.0f}% at {ev['spike_ts']:.1f} "
                f"followed by network burst at {ev['burst_ts']:.1f} "
                f"({gap:.1f}s gap — LLM inference pattern)"
            )
            
        if causality_res.get('llm_ram_loaded'):
            c_score = min(c_score + 3, 10)
            peak_ram = causality_res.get('peak_ram_gb', 0.0)
            all_evidence.append(f"LLM-scale RAM loaded: {peak_ram:.1f} GB")
            
        if causality_res.get('peak_gpu_pct', 0.0) >= GPU_SPIKE_THRESHOLD:
            c_score = min(c_score + 3, 10)
            
        total_score = min(total_score + c_score, 10)

    except Exception as e:
        print(f"[HARDWARE] Causality sequence error: {e}")

    # ── RAM ─────────────────────────────────────────────────────────────
    try:
        s, ev, r = _scan_ram()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
    except Exception as e:
        print(f"[HARDWARE] RAM scan top-level error: {e}")

    confidence = 1.0
    if not caps.has_nvidia and not caps.has_amd:
        confidence -= 0.4   # no GPU data — lower confidence

    return {
        "layer":      "hardware",
        "score":      min(total_score, 10),
        "evidence":   all_evidence,
        "confidence": max(round(confidence, 2), 0.0),
        "raw":        raw,
    }
