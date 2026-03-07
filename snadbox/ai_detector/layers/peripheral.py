"""
layers/peripheral.py — Detects AI cheating via peripheral device forensics.

Implements USB enumeration, Bluetooth detection, display monitoring, and
virtual machine detection. All checks are delta-based (only new devices
appearing AFTER baseline are flagged). Pushes ForensicEvents immediately
when new USB devices are detected.
"""

import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Set

from capability import caps

# ─── Baseline state ───────────────────────────────────────────────────────────
_usb_baseline:       Set[str] = set()   # device IDs seen at startup
_bluetooth_baseline: Set[str] = set()   # device addresses seen at startup
_display_baseline_count: int  = 0
_baseline_set = False
_baseline_lock = threading.Lock()

# ─── Active USB device set (for push event dedup) ────────────────────────────
_seen_usb_events: Set[str] = set()


# ─── USB Device Enumeration ───────────────────────────────────────────────────

def _get_usb_devices_linux() -> List[Dict[str, Any]]:
    """Parse /sys/bus/usb/devices/ for USB device class and identity info."""
    devices = []
    usb_root = "/sys/bus/usb/devices"
    if not os.path.isdir(usb_root):
        return devices

    try:
        for dev in os.listdir(usb_root):
            dev_path = os.path.join(usb_root, dev)
            if not os.path.isdir(dev_path):
                continue

            def _read(fname: str) -> str:
                try:
                    with open(os.path.join(dev_path, fname)) as f:
                        return f.read().strip()
                except Exception:
                    return ""

            id_vendor  = _read("idVendor")
            id_product = _read("idProduct")
            device_class = _read("bDeviceClass")
            manufacturer = _read("manufacturer")
            product_name = _read("product")

            if not id_vendor:
                continue

            device_id = f"{id_vendor}:{id_product}"
            devices.append({
                "device_id":    device_id,
                "device_class": device_class,
                "vendor_id":    id_vendor,
                "product_id":   id_product,
                "manufacturer": manufacturer,
                "product":      product_name,
            })
    except Exception as e:
        print(f"[PERIPHERAL] _get_usb_devices_linux error: {e}")

    return devices


def _get_usb_devices_windows() -> List[Dict[str, Any]]:
    """Use WMI Win32_PnPEntity to enumerate USB devices on Windows."""
    devices = []
    try:
        import wmi  # type: ignore
        c = wmi.WMI()

        for entity in c.Win32_PnPEntity():
            try:
                device_id = entity.DeviceID or ""
                if not device_id.startswith("USB"):
                    continue
                caption   = entity.Caption or ""
                status    = entity.Status or ""
                devices.append({
                    "device_id":    device_id,
                    "caption":      caption,
                    "status":       status,
                    "device_class": "",
                })
            except Exception:
                continue
    except Exception as e:
        print(f"[PERIPHERAL] _get_usb_devices_windows error: {e}")
    return devices


def _scan_usb_devices() -> Tuple_type:
    """Detect new USB devices appearing after baseline. Returns (score, evidence, raw)."""
    try:
        from typing import Tuple
        pass
    except Exception:
        pass

    score    = 0
    evidence = []
    raw_devices = []

    try:
        if caps.os_name == "Linux":
            devices = _get_usb_devices_linux()
        elif caps.os_name == "Windows":
            devices = _get_usb_devices_windows()
        else:
            devices = []

        with _baseline_lock:
            current_ids = {d["device_id"] for d in devices}
            new_device_ids = current_ids - _usb_baseline

        for dev in devices:
            dev_id    = dev["device_id"]
            dev_class = dev.get("device_class", "")
            raw_devices.append(dev)

            if dev_id not in new_device_ids:
                continue  # Not a new device

            # Classify by device class
            flag_type = None
            if dev_class == "03" or dev_class == "3":
                flag_type = "HID (hidden input device)"
                score = min(score + 4, 10)
            elif dev_class == "0e" or dev_class == "14":
                flag_type = "Video — additional webcam"
                score = min(score + 5, 10)
            elif dev_class == "02" or dev_class == "2":
                flag_type = "Communications — USB network adapter"
                score = min(score + 4, 10)
            else:
                score = min(score + 2, 10)
                flag_type = f"class {dev_class or 'unknown'}"

            product = dev.get("product") or dev.get("caption") or dev_id
            ev_str  = f"New USB device after session start: {product} ({flag_type})"
            evidence.append(ev_str)

            # Push ForensicEvent immediately for new USB devices
            if dev_id not in _seen_usb_events:
                _seen_usb_events.add(dev_id)
                _push_usb_event(ev_str, score, dev)

    except Exception as e:
        print(f"[PERIPHERAL] _scan_usb_devices error: {e}")

    return score, evidence, raw_devices


def _push_usb_event(description: str, score: int, raw: dict) -> None:
    """Push a new USB device ForensicEvent immediately."""
    try:
        from api import push_event
        from shared.schemas import ForensicEvent
        push_event(ForensicEvent(
            timestamp=time.time(),
            source="varchas",
            layer="peripheral",
            signal="usb_new_device",
            value=min(score / 10.0, 1.0),
            raw=raw,
            severity="high",
            description=description,
        ))
    except Exception:
        pass


# ─── Bluetooth Detection ──────────────────────────────────────────────────────

def _get_bluetooth_devices_linux() -> List[Dict[str, Any]]:
    """Parse /var/lib/bluetooth/ or use bluetoothctl to list connected devices."""
    devices = []
    try:
        result = subprocess.run(
            ["bluetoothctl", "devices", "Connected"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                # format: Device XX:XX:XX:XX:XX:XX Name
                parts = line.strip().split(" ", 2)
                if len(parts) >= 3 and parts[0] == "Device":
                    addr = parts[1]
                    name = parts[2]
                    devices.append({
                        "address": addr,
                        "name":    name,
                        "status":  "connected",
                    })
    except FileNotFoundError:
        # bluetoothctl not available — try /var/lib/bluetooth/
        try:
            bt_root = "/var/lib/bluetooth"
            if os.path.isdir(bt_root):
                for adapter in os.listdir(bt_root):
                    adapter_path = os.path.join(bt_root, adapter)
                    if os.path.isdir(adapter_path):
                        for dev_addr in os.listdir(adapter_path):
                            info_path = os.path.join(adapter_path, dev_addr, "info")
                            if os.path.isfile(info_path):
                                name = ""
                                try:
                                    with open(info_path) as f:
                                        for line in f:
                                            if line.startswith("Name="):
                                                name = line.strip().split("=", 1)[1]
                                except Exception:
                                    pass
                                devices.append({
                                    "address": dev_addr,
                                    "name":    name,
                                    "status":  "paired",
                                })
        except Exception as e:
            print(f"[PERIPHERAL] bluetooth fallback error: {e}")
    except Exception as e:
        print(f"[PERIPHERAL] bluetoothctl error: {e}")
    return devices


def _get_bluetooth_devices_windows() -> List[Dict[str, Any]]:
    """Use WMI Win32_PnPEntity filtered by BTHENUM to detect bluetooth devices."""
    devices = []
    try:
        import wmi  # type: ignore
        c = wmi.WMI()
        for entity in c.Win32_PnPEntity():
            try:
                dev_id = entity.DeviceID or ""
                if "BTHENUM" not in dev_id and "BTH" not in dev_id:
                    continue
                devices.append({
                    "address": dev_id,
                    "name":    entity.Caption or "",
                    "status":  "detected",
                })
            except Exception:
                continue
    except Exception as e:
        print(f"[PERIPHERAL] bluetooth WMI error: {e}")
    return devices


def _scan_bluetooth() -> tuple:
    """Detect new Bluetooth devices appearing after baseline.

    Returns (score, evidence, raw_list).
    """
    score    = 0
    evidence = []
    raw_list = []

    try:
        if caps.os_name == "Linux":
            devices = _get_bluetooth_devices_linux()
        elif caps.os_name == "Windows":
            devices = _get_bluetooth_devices_windows()
        else:
            devices = []

        with _baseline_lock:
            current_addrs = {d["address"] for d in devices}
            new_addrs = current_addrs - _bluetooth_baseline

        for dev in devices:
            raw_list.append(dev)
            if dev["address"] not in new_addrs:
                continue

            name_lower = (dev.get("name") or "").lower()
            dev_type   = "unknown device"

            # Classify: earpiece / headset pattern
            if any(kw in name_lower for kw in ["earphone", "headphone", "headset", "airpod", "earbud", "buds"]):
                dev_type = "earpiece/headset"
                score = min(score + 5, 10)
                evidence.append(
                    f"New Bluetooth earpiece detected: '{dev.get('name')}' "
                    f"({dev['address']}) — possible audio injection"
                )
            # Phone tethering (PAN profile)
            elif any(kw in name_lower for kw in ["phone", "pixel", "iphone", "galaxy", "redmi", "oneplus"]):
                dev_type = "phone — possible tethering"
                score = min(score + 4, 10)
                evidence.append(
                    f"New Bluetooth phone detected: '{dev.get('name')}' "
                    f"({dev['address']}) — possible PAN tethering"
                )
            else:
                score = min(score + 2, 10)
                evidence.append(
                    f"New Bluetooth device after session start: "
                    f"'{dev.get('name')}' ({dev['address']})"
                )

    except Exception as e:
        print(f"[PERIPHERAL] _scan_bluetooth error: {e}")

    return score, evidence, raw_list


# ─── Display Monitoring ───────────────────────────────────────────────────────

def _scan_displays() -> tuple:
    """Count active monitors and detect remote desktop / screen mirroring.

    Returns (score, evidence, displays_dict).
    """
    score    = 0
    evidence = []
    raw: Dict[str, Any] = {
        "monitor_count":   0,
        "is_remote":       False,
        "session_name":    "",
        "resolutions":     [],
    }

    try:
        if caps.os_name == "Windows":
            _scan_displays_windows(score, evidence, raw)
        elif caps.os_name == "Linux":
            _scan_displays_linux(score, evidence, raw)

        # Flag if monitor count changed mid-session
        with _baseline_lock:
            monitor_count = raw.get("monitor_count", 0)
            if _display_baseline_count > 0 and monitor_count != _display_baseline_count:
                score = min(score + 3, 10)
                evidence.append(
                    f"Monitor count changed mid-session: "
                    f"{_display_baseline_count} → {monitor_count}"
                )

        if raw.get("is_remote"):
            score = min(score + 5, 10)
            evidence.append(
                f"Remote desktop session detected: {raw.get('session_name', '')}"
            )

    except Exception as e:
        print(f"[PERIPHERAL] _scan_displays error: {e}")

    return score, evidence, raw


def _scan_displays_windows(score, evidence, raw) -> None:
    """Windows display scan via ctypes EnumDisplayMonitors."""
    try:
        import ctypes
        monitors = []

        def _enum_cb(hMonitor, hdcMonitor, lprcMonitor, dwData):
            try:
                monitors.append(hMonitor)
            except Exception:
                pass
            return True

        MonitorEnumProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_ulong, ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_long), ctypes.c_double
        )
        ctypes.windll.user32.EnumDisplayMonitors(
            None, None, MonitorEnumProc(_enum_cb), 0
        )
        raw["monitor_count"] = len(monitors)

        # RDP detection via SESSIONNAME env var
        session_name = os.environ.get("SESSIONNAME", "")
        raw["session_name"] = session_name
        if session_name.startswith("RDP-Tcp"):
            raw["is_remote"] = True
    except Exception as e:
        print(f"[PERIPHERAL] Windows display scan error: {e}")


def _scan_displays_linux(score, evidence, raw) -> None:
    """Linux display scan via xrandr."""
    try:
        result = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            connected = [
                line for line in result.stdout.splitlines()
                if " connected" in line
            ]
            raw["monitor_count"] = len(connected)
            resolutions = []
            for line in connected:
                parts = line.split()
                if len(parts) >= 3:
                    resolutions.append(parts[2])
            raw["resolutions"] = resolutions
    except FileNotFoundError:
        # xrandr not available — check /sys/class/drm
        try:
            drm_path = "/sys/class/drm"
            if os.path.isdir(drm_path):
                count = 0
                for entry in os.listdir(drm_path):
                    status_path = os.path.join(drm_path, entry, "status")
                    if os.path.isfile(status_path):
                        try:
                            with open(status_path) as f:
                                if f.read().strip() == "connected":
                                    count += 1
                        except Exception:
                            pass
                raw["monitor_count"] = count
        except Exception as e:
            print(f"[PERIPHERAL] drm display scan error: {e}")
    except Exception as e:
        print(f"[PERIPHERAL] xrandr error: {e}")

    # Remote desktop detection on Linux
    display = os.environ.get("DISPLAY", "")
    x11_socket = "/tmp/.X11-unix"
    raw["session_name"] = display
    if display and not display.startswith(":"):
        # DISPLAY set to a remote host
        raw["is_remote"] = True


# ─── Virtual Machine Detection ───────────────────────────────────────────────

def _scan_virtual_machine() -> tuple:
    """Detect VM/hypervisor environment. Containers are NOT scored.

    Returns (score, evidence, vm_dict).
    """
    score    = 0
    evidence = []
    raw: Dict[str, Any] = {
        "is_vm":             False,
        "is_container":      False,
        "hypervisor_type":   "",
        "vm_artifacts":      [],
    }

    try:
        # ── Container detection (do NOT score) ──────────────────────
        if os.path.isfile("/.dockerenv"):
            raw["is_container"] = True
            return score, evidence, raw

        try:
            with open("/proc/1/cgroup") as f:
                cgroup_content = f.read()
            if "docker" in cgroup_content or "containerd" in cgroup_content or "kubepods" in cgroup_content:
                raw["is_container"] = True
                return score, evidence, raw
        except Exception:
            pass

        # ── VM detection ─────────────────────────────────────────────
        if caps.os_name == "Linux":
            _detect_vm_linux(raw)
        elif caps.os_name == "Windows":
            _detect_vm_windows(raw)

        # VM driver artifact check (psutil process names)
        try:
            import psutil  # type: ignore
            vm_drivers = ["vmtoolsd", "vboxservice", "vboxclient", "vmwaretray"]
            for proc in psutil.process_iter(["name"]):
                try:
                    name_lower = (proc.info.get("name") or "").lower()
                    for drv in vm_drivers:
                        if drv in name_lower:
                            raw["vm_artifacts"].append(drv)
                            raw["is_vm"] = True
                            break
                except Exception:
                    continue
        except Exception:
            pass

        if raw["is_vm"]:
            score = min(score + 5, 10)
            hv = raw.get("hypervisor_type", "unknown")
            evidence.append(
                f"Virtual machine detected: {hv} "
                f"(suspicious for interview — possible screenshot evasion)"
            )

    except Exception as e:
        print(f"[PERIPHERAL] _scan_virtual_machine error: {e}")

    return score, evidence, raw


def _detect_vm_linux(raw: dict) -> None:
    """Linux VM detection via /proc/cpuinfo and /sys/class/dmi."""
    try:
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read()
        if "hypervisor" in cpuinfo.lower():
            raw["is_vm"] = True
            raw["hypervisor_type"] = "hypervisor (from /proc/cpuinfo)"
    except Exception:
        pass

    # DMI product name
    dmi_paths = [
        "/sys/class/dmi/id/product_name",
        "/sys/class/dmi/id/sys_vendor",
    ]
    for dmi_path in dmi_paths:
        try:
            with open(dmi_path) as f:
                value = f.read().strip().lower()
            for keyword in ["virtual", "vmware", "virtualbox", "hvm", "kvm", "qemu", "xen"]:
                if keyword in value:
                    raw["is_vm"] = True
                    raw["hypervisor_type"] = keyword
                    break
        except Exception:
            pass


def _detect_vm_windows(raw: dict) -> None:
    """Windows VM detection via WMI Win32_ComputerSystem.Model."""
    try:
        import wmi  # type: ignore
        c = wmi.WMI()
        for cs in c.Win32_ComputerSystem():
            model = (cs.Model or "").lower()
            for keyword in ["virtual", "vmware", "virtualbox", "hvm"]:
                if keyword in model:
                    raw["is_vm"] = True
                    raw["hypervisor_type"] = keyword
                    break
    except Exception as e:
        print(f"[PERIPHERAL] WMI VM detect error: {e}")


# ─── Baseline Setting ─────────────────────────────────────────────────────────

def set_peripheral_baseline() -> None:
    """Record USB, Bluetooth, and display state at session startup."""
    global _display_baseline_count

    try:
        if caps.os_name == "Linux":
            usb_devices = _get_usb_devices_linux()
            bt_devices  = _get_bluetooth_devices_linux()
        elif caps.os_name == "Windows":
            usb_devices = _get_usb_devices_windows()
            bt_devices  = _get_bluetooth_devices_windows()
        else:
            usb_devices = []
            bt_devices  = []

        with _baseline_lock:
            _usb_baseline.clear()
            _usb_baseline.update(d["device_id"] for d in usb_devices)

            _bluetooth_baseline.clear()
            _bluetooth_baseline.update(d["address"] for d in bt_devices)

        # Display baseline
        _, _, display_raw = _scan_displays()
        _display_baseline_count = display_raw.get("monitor_count", 0)

        print(
            f"[STARTUP] Peripheral baseline set — "
            f"USB: {len(_usb_baseline)} devices, "
            f"BT: {len(_bluetooth_baseline)} devices, "
            f"monitors: {_display_baseline_count}"
        )
    except Exception as e:
        print(f"[PERIPHERAL] set_peripheral_baseline error: {e}")


# ─── ForensicEvent converter ──────────────────────────────────────────────────

def to_forensic_events(scan_result: dict) -> list:
    """Convert a peripheral layer result dict into a list of ForensicEvent objects."""
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
                "usb_new_device"     if "USB" in ev_str else
                "bluetooth_earpiece" if "earpiece" in ev_str.lower() or "headset" in ev_str.lower() else
                "vm_detected"        if "Virtual machine" in ev_str else
                "peripheral"
            )
            event = ForensicEvent(
                timestamp=time.time(),
                source="varchas",
                layer=scan_result.get("layer", "peripheral"),
                signal=signal,
                value=value,
                raw=scan_result.get("raw", {}),
                severity=severity,
                description=ev_str,
            )
            events.append(event)
    except Exception as e:
        print(f"[PERIPHERAL] to_forensic_events error: {e}")
    return events


# ─── Public API ───────────────────────────────────────────────────────────────

# Fix type hint — local workaround for tuple return type annotation
Tuple_type = tuple


def run_peripheral_scan() -> dict:
    """Run USB, Bluetooth, display, and VM detection; return standard layer result dict."""
    all_evidence = []
    raw: Dict[str, Any] = {}
    total_score   = 0

    try:
        s, ev, usb_raw = _scan_usb_devices()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw["usb_devices"] = usb_raw
    except Exception as e:
        print(f"[PERIPHERAL] USB scan error: {e}")
        raw["usb_error"] = str(e)

    try:
        s, ev, bt_raw = _scan_bluetooth()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw["bluetooth"] = bt_raw
    except Exception as e:
        print(f"[PERIPHERAL] Bluetooth scan error: {e}")
        raw["bt_error"] = str(e)

    try:
        s, ev, disp_raw = _scan_displays()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw["displays"] = disp_raw
    except Exception as e:
        print(f"[PERIPHERAL] Display scan error: {e}")
        raw["display_error"] = str(e)

    try:
        s, ev, vm_raw = _scan_virtual_machine()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw["virtual_machine"] = vm_raw
    except Exception as e:
        print(f"[PERIPHERAL] VM scan error: {e}")
        raw["vm_error"] = str(e)

    confidence = 0.8 if (caps.os_name in ("Linux", "Windows")) else 0.4

    return {
        "layer":      "peripheral",
        "score":      min(total_score, 10),
        "evidence":   all_evidence,
        "confidence": round(confidence, 2),
        "raw":        raw,
    }
