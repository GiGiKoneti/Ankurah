"""
capability.py — Detects what hardware, OS, and system features are available.

Runs once at startup and exports a singleton `caps` instance.
All detection layer modules import `caps` from this module.
"""

import os
import sys
import subprocess
import platform


class Capabilities:
    """Probes system capabilities at startup; sets boolean flags for every layer."""

    def __init__(self):
        """Detect OS, privileges, GPU, clipboard, window API, and network access."""
        self.os_name           = self._detect_os()
        self.is_admin          = self._detect_admin()
        self.has_nvidia        = self._detect_nvidia()
        self.has_amd           = self._detect_amd()
        self.has_clipboard     = self._detect_clipboard()
        self.has_window_api    = self._detect_window_api()
        self.can_read_connections = self._detect_connections()
        self._print_report()

    # ── OS ────────────────────────────────────────────────────────────────────

    def _detect_os(self) -> str:
        """Return 'Windows', 'Linux', or 'Darwin' based on platform."""
        try:
            system = platform.system()
            if system in ("Windows", "Linux", "Darwin"):
                return system
            return system or "Unknown"
        except Exception as e:
            print(f"[CAPABILITY] error detecting OS: {e}")
            return "Unknown"

    # ── Privileges ────────────────────────────────────────────────────────────

    def _detect_admin(self) -> bool:
        """Return True if the process is running with admin/root privileges."""
        try:
            if self.os_name == "Windows":
                import ctypes
                return bool(ctypes.windll.shell32.IsUserAnAdmin())
            else:
                return os.geteuid() == 0
        except Exception as e:
            print(f"[CAPABILITY] error detecting admin: {e}")
            return False

    # ── GPU Detection ─────────────────────────────────────────────────────────

    def _detect_nvidia(self) -> bool:
        """Return True if pynvml initialises and at least one NVIDIA GPU is present."""
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            return count > 0
        except Exception as e:
            print(f"[CAPABILITY] NVIDIA GPU not detected: {e}")
            return False

    def _detect_amd(self) -> bool:
        """Return True if an AMD GPU is detected via WMI (Windows) or /sys/class/drm (Linux)."""
        try:
            if self.os_name == "Windows":
                import wmi  # type: ignore
                c = wmi.WMI()
                for gpu in c.Win32_VideoController():
                    name = (gpu.Name or "").lower()
                    if "amd" in name or "radeon" in name:
                        return True
                return False
            elif self.os_name == "Linux":
                drm_path = "/sys/class/drm"
                if not os.path.isdir(drm_path):
                    return False
                for entry in os.listdir(drm_path):
                    vendor_path = os.path.join(drm_path, entry, "device", "vendor")
                    if os.path.isfile(vendor_path):
                        with open(vendor_path) as f:
                            # AMD vendor ID is 0x1002
                            if "1002" in f.read():
                                return True
                return False
            elif self.os_name == "Darwin":
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True, text=True, timeout=5
                )
                return "amd" in result.stdout.lower() or "radeon" in result.stdout.lower()
            return False
        except Exception as e:
            print(f"[CAPABILITY] AMD GPU detection error: {e}")
            return False

    # ── Clipboard ─────────────────────────────────────────────────────────────

    def _detect_clipboard(self) -> bool:
        """Return True if pyperclip can access the clipboard without error."""
        try:
            import pyperclip  # type: ignore
            pyperclip.paste()
            return True
        except Exception as e:
            print(f"[CAPABILITY] clipboard not available: {e}")
            return False

    # ── Window API ────────────────────────────────────────────────────────────

    def _detect_window_api(self) -> bool:
        """Return True if window-title enumeration is available on this platform."""
        try:
            if self.os_name == "Windows":
                import ctypes
                # Verify windll.user32 is accessible
                _ = ctypes.windll.user32.GetForegroundWindow
                return True
            elif self.os_name == "Linux":
                result = subprocess.run(
                    ["which", "xdotool"],
                    capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    return True
                # Fallback: try wmctrl
                result2 = subprocess.run(
                    ["which", "wmctrl"],
                    capture_output=True, text=True, timeout=3
                )
                return result2.returncode == 0
            elif self.os_name == "Darwin":
                result = subprocess.run(
                    ["which", "osascript"],
                    capture_output=True, text=True, timeout=3
                )
                return result.returncode == 0
            return False
        except Exception as e:
            print(f"[CAPABILITY] window API not available: {e}")
            return False

    # ── Network Connections ───────────────────────────────────────────────────

    def _detect_connections(self) -> bool:
        """Return True if psutil.net_connections() can be called without AccessDenied."""
        try:
            import psutil  # type: ignore
            psutil.net_connections(kind="inet")
            return True
        except psutil.AccessDenied:
            print("[CAPABILITY] psutil.net_connections() requires elevated privileges")
            return False
        except Exception as e:
            print(f"[CAPABILITY] net_connections error: {e}")
            return False

    # ── Startup Report ────────────────────────────────────────────────────────

    def _print_report(self):
        """Print a human-readable startup capability report to stdout."""
        def sym(flag: bool) -> str:
            return "✅" if flag else "⚠️ "

        print("\n╔══════════════════════════════════════════╗")
        print("║        AI DETECTOR — CAPABILITY REPORT   ║")
        print("╚══════════════════════════════════════════╝")
        print(f"  OS                : {self.os_name}")
        print(f"  {sym(self.is_admin)} Admin/Root")
        print(f"  {sym(self.has_nvidia)} NVIDIA GPU (pynvml)")
        print(f"  {sym(self.has_amd)} AMD GPU")
        print(f"  {sym(self.has_clipboard)} Clipboard access")
        print(f"  {sym(self.has_window_api)} Window title API")
        print(f"  {sym(self.can_read_connections)} Network connection table")
        print()


# Singleton — import this, never instantiate Capabilities() yourself
caps = Capabilities()
