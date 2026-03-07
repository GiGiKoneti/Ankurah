"""
layers/stealth_windows.py — ETW-based stealth overlay window detection.

This is a Windows-only layer. It identifies hidden, transparent, tool-windows
often used by cheating overlays and remote injection helpers.
"""

import ctypes
import os
import threading
import time
from typing import List, Dict, Any

from config import WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW, THREAT_PROCESSES
from capability import caps


_SYSTEM_PROC_WHITELIST = {
    'explorer.exe', 'dwm.exe', 'searchhost.exe', 'shellexperiencehost.exe',
    'startmenuexperiencehost.exe', 'textinputhost.exe', 'sihost.exe',
    'taskhostw.exe', 'ctfmon.exe', 'fontdrvhost.exe', 'winlogon.exe',
    'csrss.exe', 'svchost.exe', 'nvidia share.exe', 'igfxem.exe',
    'amdow.exe', 'radeonsoftware.exe', 'discord.exe', 'slack.exe',
    'teams.exe', 'zoom.exe', 'chrome.exe', 'msedge.exe', 'firefox.exe',
}

def _get_proc_name(pid: int) -> str:
    """Lookup process name from PID via ctypes OpenProcess + GetModuleBaseName or fallback to psutil."""
    try:
        if caps.os_name == "Windows":
            import ctypes.wintypes
            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            
            h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
            if h_process:
                buf = ctypes.create_unicode_buffer(512)
                if psapi.GetModuleBaseNameW(h_process, 0, buf, ctypes.sizeof(buf)):
                    kernel32.CloseHandle(h_process)
                    return buf.value
                kernel32.CloseHandle(h_process)
    except Exception:
        pass
        
    try:
        import psutil # type: ignore
        return psutil.Process(pid).name()
    except Exception:
        return ""


def _enumerate_stealth_windows() -> List[Dict[str, Any]]:
    """Scan all windows for layered + transparent + toolwindow patterns not in whitelist."""
    stealth_windows = []
    
    try:
        import ctypes.wintypes
        user32 = ctypes.windll.user32
        
        def _enum_callback(hwnd, lParam):
            try:
                ex_style = user32.GetWindowLongW(hwnd, -20) # GWL_EXSTYLE
                
                is_layered = bool(ex_style & WS_EX_LAYERED)
                if not is_layered:
                    return True
                    
                is_transparent = bool(ex_style & WS_EX_TRANSPARENT)
                is_toolwindow  = bool(ex_style & WS_EX_TOOLWINDOW)
                stealth = is_transparent or is_toolwindow
                
                if stealth:
                    length = user32.GetWindowTextLengthW(hwnd)
                    title = ""
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        title = buf.value
                        
                    pid_buf = ctypes.wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_buf))
                    pid = pid_buf.value
                    
                    proc_name = _get_proc_name(pid)
                    if proc_name.lower() in _SYSTEM_PROC_WHITELIST:
                        return True
                        
                    is_visible = bool(user32.IsWindowVisible(hwnd))
                    
                    stealth_windows.append({
                        'hwnd': hwnd,
                        'title': title,
                        'pid': pid,
                        'proc_name': proc_name,
                        'ex_style_hex': hex(ex_style),
                        'is_transparent': is_transparent,
                        'is_toolwindow': is_toolwindow,
                        'is_layered': is_layered,
                        'is_visible': is_visible,
                    })
            except Exception:
                pass
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(_enum_callback), 0)
        
    except Exception as e:
        print(f"[STEALTH] enum windows error: {e}")
        
    return stealth_windows


def run_stealth_window_scan() -> dict:
    """Scan for stealth overlay windows (Windows only)."""
    if caps.os_name != "Windows":
        return {
            'layer': 'stealth_windows',
            'score': 0,
            'evidence': [],
            'confidence': 0.0,
            'raw': {'note': 'Windows only'},
        }

    score = 0
    evidence: List[str] = []
    
    stealth_windows = _enumerate_stealth_windows()
    
    for w in stealth_windows:
        proc_name_lower = w['proc_name'].lower()
        
        # Check if the process name fragment matches THREAT_PROCESSES
        match_threat = False
        for frag in THREAT_PROCESSES:
            if frag in proc_name_lower:
                match_threat = True
                break
                
        if match_threat:
            score += 8
        else:
            score += 5
            
        evidence.append(f"Stealth overlay window: proc='{w['proc_name']}' PID={w['pid']} styles={w['ex_style_hex']}")
        
    confidence = 0.9 if stealth_windows else 1.0

    return {
        'layer': 'stealth_windows',
        'score': min(score, 10),
        'evidence': evidence,
        'confidence': confidence,
        'raw': {'stealth_windows': stealth_windows},
    }
