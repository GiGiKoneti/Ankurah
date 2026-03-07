# CANDIDATE SETUP:
# 1. Double click this file or: python truthlens_agent.py
# 2. That's it. Nothing else needed.

import sys
sys.dont_write_bytecode = True

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — AUTO INSTALL
# ══════════════════════════════════════════════════════════════════════════════
def _bootstrap():
    import subprocess, sys, os
    
    REQUIRED = [
        'psutil',
        'pyperclip',
        'requests',
        'cryptography'
    ]
    
    try:
        import pip
    except ImportError:
        subprocess.run(
            [sys.executable, '-m', 'ensurepip', '--quiet'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    
    for pkg in REQUIRED:
        try:
            __import__(pkg)
        except ImportError:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install',
                 pkg, '--quiet', '--disable-pip-version-check',
                 '--no-warn-script-location'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    
    try:
        __import__('pynvml')
    except ImportError:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install',
             'pynvml', '--quiet'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30
        )

_bootstrap()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — GO INVISIBLE
# ══════════════════════════════════════════════════════════════════════════════
import os
import subprocess

def _go_invisible():
    if sys.platform == 'win32':
        if 'pythonw' not in sys.executable.lower():
            pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
            if os.path.exists(pythonw):
                subprocess.Popen(
                    [pythonw, os.path.abspath(__file__)] + sys.argv[1:],
                    creationflags=0x08000000,
                    close_fds=True
                )
                sys.exit(0)
    else:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    
    try:
        import setproctitle  # type: ignore
        setproctitle.setproctitle('MeetHelper')
    except Exception:
        pass

_go_invisible()

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS AFTER BOOTSTRAP
# ══════════════════════════════════════════════════════════════════════════════
import fcntl
import hashlib
import hmac
import json
import platform
import re
import signal
import socket
import threading
import time
import uuid
from collections import deque

try: import psutil
except ImportError: psutil = None  # type: ignore

try: import pyperclip
except ImportError: pyperclip = None

try: 
    import pynvml
    pynvml.nvmlInit()
except Exception: 
    pynvml = None

try: import requests
except ImportError: requests = None


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — AUTO CONNECT TO SERVER
# ══════════════════════════════════════════════════════════════════════════════
SERVER_URL = "http://172.25.72.180:8000"
SESSION_ID = str(uuid.uuid4())
AGENT_SELF_HASH = ''

_LOG_PATH = ''
_LOG_LOCK = threading.Lock()
_LOG_SEQ = 0
_LOG_PREV_HASH = ''
_EVENTS_IN_MEMORY = []
_HW_HISTORY = deque(maxlen=300)
_HW_LOCK = threading.Lock()
_SESSION_START = time.time()
_TERMINATE_FLAG = threading.Event()
_TAMPER_DETECTED = False

_THREAT_PROCESSES_FOUND = []
_AI_DOMAINS_FOUND = []
_AI_PORTS_FOUND = []
_AI_WINDOWS_FOUND = []
_PASTES_COUNT = 0
_CAUSALITY_CHAINS = 0
_STATE_LOCK = threading.Lock()

THREAT_PROCESSES = {
    'parakeet','interviewcoder','shadecoder','cluely',
    'interviewsolver','yoodli','ngrok','anydesk',
    'teamviewer','obs64','manycam','voicemeeter',
    'ollama','lmstudio','llamafile'
}

AI_PORTS = {11434, 1234, 8080, 7860}

AI_DOMAINS = [
    'api.openai.com','api.anthropic.com','api.groq.com',
    'openrouter.ai','ngrok.io','ngrok.com','cluely.ai',
    'anydesk.com','teamviewer.com','parakeet-ai.com',
    'interviewcoder.co','api.mistral.ai','api.together.xyz',
    'generativelanguage.googleapis.com'
]

AI_WINDOW_KEYWORDS = [
    'chatgpt','claude','gemini','copilot',
    'cluely','interviewcoder','parakeet','ollama','perplexity'
]
_KW_PATTERNS = [re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE) for kw in AI_WINDOW_KEYWORDS]


def _http_post(path: str, payload: dict) -> dict:
    if not requests: return {}
    try:
        resp = requests.post(
            f"{SERVER_URL.rstrip('/')}{path}",
            json=payload,
            headers={'X-Session-ID': SESSION_ID},
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def _http_get(path: str) -> dict:
    if not requests: return {}
    try:
        resp = requests.get(
            f"{SERVER_URL.rstrip('/')}{path}",
            headers={'X-Session-ID': SESSION_ID},
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def _log_path() -> str:
    short_id = SESSION_ID[:8]
    if sys.platform == 'win32':
        tmp = os.environ.get('TEMP', os.environ.get('TMP', 'C:\\Temp'))
        path = os.path.join(tmp, f'meethelper_{short_id}.tmp')
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(path, 2)
        except Exception: pass
        return path
    else:
        return f'/tmp/.mh_{short_id}'


def _lock_file(fh):
    try:
        if sys.platform == 'win32':
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    except Exception: pass

def _unlock_file(fh):
    try:
        if sys.platform == 'win32':
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except Exception: pass


def _write_log_entry(event_type: str, data: dict):
    global _LOG_SEQ, _LOG_PREV_HASH
    if not _LOG_PATH: return
    try:
        with _LOG_LOCK:
            entry = {
                'seq': _LOG_SEQ,
                'ts': time.time(),
                'event': event_type,
                'data': data,
                'prev_hash': _LOG_PREV_HASH
            }
            serialised = json.dumps(entry, sort_keys=True, separators=(',', ':'))
            mac = hmac.new(SESSION_ID.encode(), serialised.encode(), hashlib.sha256).hexdigest()
            entry['hmac'] = mac

            line = json.dumps(entry, separators=(',', ':')) + '\n'
            with open(_LOG_PATH, 'a', encoding='utf-8') as fh:
                _lock_file(fh)
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
                _unlock_file(fh)

            _LOG_PREV_HASH = hashlib.sha256(line.rstrip('\n').encode()).hexdigest()
            _LOG_SEQ += 1
            _EVENTS_IN_MEMORY.append(entry)
    except Exception: pass


# ══════════════════════════════════════════════════════════════════════════════
# TAMPER PROTECTION
# ══════════════════════════════════════════════════════════════════════════════

def _compute_self_hash() -> str:
    try:
        with open(os.path.abspath(__file__), 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception: return ''

def _verify_startup_integrity():
    global AGENT_SELF_HASH, _LOG_PREV_HASH
    AGENT_SELF_HASH = _compute_self_hash()
    _LOG_PREV_HASH = hashlib.sha256(SESSION_ID.encode()).hexdigest()
    _http_post('/register', {'session_id': SESSION_ID, 'hash': AGENT_SELF_HASH})

def _integrity_monitor():
    global _TAMPER_DETECTED
    while not _TERMINATE_FLAG.is_set():
        try:
            time.sleep(60)
            current = _compute_self_hash()
            if current and current != AGENT_SELF_HASH:
                with _STATE_LOCK: _TAMPER_DETECTED = True
                _write_log_entry('TAMPER', {'desc': 'Self-hash mismatch'})
                _http_post('/event', {'event': 'TAMPER', 'data': {'desc': 'Self-hash mismatch'}})
        except Exception: pass


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — ALL MONITORING
# ══════════════════════════════════════════════════════════════════════════════

def _process_monitor():
    _seen_pids, _seen_ports = set(), set()
    while not _TERMINATE_FLAG.is_set():
        try:
            if psutil:
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        name = (proc.info.get('name') or '').lower()
                        exe = (proc.info.get('exe') or '').lower()
                        pid = proc.pid
                        if pid in _seen_pids: continue
                        for threat in THREAT_PROCESSES:
                            if threat in name or threat in exe:
                                _seen_pids.add(pid)
                                with _STATE_LOCK:
                                    if threat not in _THREAT_PROCESSES_FOUND:
                                        _THREAT_PROCESSES_FOUND.append(threat)
                                data = {'name': name, 'match': threat, 'pid': pid}
                                _write_log_entry('THREAT_PROCESS', data)
                                _http_post('/event', {'event': 'THREAT_PROCESS', 'data': data})
                                break
                    except Exception: continue

                for conn in psutil.net_connections(kind='inet'):
                    try:
                        if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port in AI_PORTS:
                            port = conn.laddr.port
                            if port not in _seen_ports:
                                _seen_ports.add(port)
                                with _STATE_LOCK:
                                    if port not in _AI_PORTS_FOUND:
                                        _AI_PORTS_FOUND.append(port)
                                data = {'port': port, 'pid': conn.pid}
                                _write_log_entry('AI_PORT', data)
                                _http_post('/event', {'event': 'AI_PORT', 'data': data})
                    except Exception: continue
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=2.0)


def _network_monitor():
    _seen_domains, _rdns_cache = set(), {}
    def _rdns(ip):
        if ip in _rdns_cache: return _rdns_cache[ip]
        old_to = socket.getdefaulttimeout()
        socket.setdefaulttimeout(1.0)
        try: hostname = socket.gethostbyaddr(ip)[0]
        except Exception: hostname = None
        finally: socket.setdefaulttimeout(old_to)
        _rdns_cache[ip] = hostname
        return hostname

    while not _TERMINATE_FLAG.is_set():
        try:
            if psutil:
                conns = psutil.net_connections(kind='inet')
                for conn in conns:
                    try:
                        if not conn.raddr: continue
                        remote_ip = conn.raddr.ip
                        if not remote_ip or remote_ip.startswith('127.') or remote_ip == '::1': continue
                        hostname = _rdns(remote_ip)
                        if not hostname: continue
                        for domain in AI_DOMAINS:
                            if hostname == domain or hostname.endswith('.' + domain):
                                key = f'{domain}:{remote_ip}'
                                if key not in _seen_domains:
                                    _seen_domains.add(key)
                                    with _STATE_LOCK:
                                        if domain not in _AI_DOMAINS_FOUND:
                                            _AI_DOMAINS_FOUND.append(domain)
                                    data = {'domain': domain, 'hostname': hostname}
                                    _write_log_entry('AI_DOMAIN', data)
                                    _http_post('/event', {'event': 'AI_DOMAIN', 'data': data})
                                break
                    except Exception: continue
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=1.0)


def _clipboard_monitor():
    global _PASTES_COUNT
    _last_hash = ''
    while not _TERMINATE_FLAG.is_set():
        try:
            if pyperclip:
                content = pyperclip.paste()
                if content and len(content) > 500:
                    chash = hashlib.sha256(content.encode('utf-8', errors='replace')).hexdigest()
                    if chash != _last_hash:
                        _last_hash = chash
                        with _STATE_LOCK: _PASTES_COUNT += 1
                        data = {'char_count': len(content), 'hash': chash}
                        _write_log_entry('LARGE_PASTE', data)
                        _http_post('/event', {'event': 'LARGE_PASTE', 'data': data})
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=0.2)


def _get_window_titles() -> list:
    titles = []
    try:
        if sys.platform == 'win32':
            import ctypes, ctypes.wintypes
            _titles_ref = []
            def _cb(hwnd, _):
                try:
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        if buf.value.strip(): _titles_ref.append(buf.value)
                except Exception: pass
                return True
            EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
            ctypes.windll.user32.EnumWindows(EnumProc(_cb), 0)
            titles = _titles_ref
        elif sys.platform == 'linux':
            try:
                res = subprocess.run(['xdotool','search','--onlyvisible','--name','.*'], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    for wid in res.stdout.splitlines():
                        name_res = subprocess.run(['xdotool','getwindowname',wid], capture_output=True, text=True, timeout=1)
                        if name_res.returncode == 0 and name_res.stdout.strip(): titles.append(name_res.stdout.strip())
            except Exception: pass
        elif sys.platform == 'darwin':
            res = subprocess.run(['osascript','-e','tell application "System Events" to get name of every window of every process'], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                raw = res.stdout.replace('{','').replace('}','').replace('"','')
                titles = [t.strip() for t in raw.split(',') if t.strip()]
    except Exception: pass
    return titles


def _window_monitor():
    _seen_windows = set()
    while not _TERMINATE_FLAG.is_set():
        try:
            for title in _get_window_titles():
                for i, pattern in enumerate(_KW_PATTERNS):
                    kw = AI_WINDOW_KEYWORDS[i]
                    if pattern.search(title):
                        key = f'{kw}:{title[:50]}'
                        if key not in _seen_windows:
                            _seen_windows.add(key)
                            with _STATE_LOCK:
                                if kw not in _AI_WINDOWS_FOUND: _AI_WINDOWS_FOUND.append(kw)
                            data = {'keyword': kw, 'title': title[:50]}
                            _write_log_entry('AI_WINDOW', data)
                            _http_post('/event', {'event': 'AI_WINDOW', 'data': data})
                        break
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=1.0)


def _hardware_monitor():
    global _CAUSALITY_CHAINS
    _last_causality_ts = 0.0
    while not _TERMINATE_FLAG.is_set():
        try:
            sample = {'ts': time.time()}
            if psutil:
                try: sample['cpu_pct'] = psutil.cpu_percent()
                except Exception: sample['cpu_pct'] = 0.0
                try: sample['ram_gb'] = psutil.virtual_memory().used / 1e9
                except Exception: sample['ram_gb'] = 0.0
                try: sample['net_recv_kb'] = psutil.net_io_counters().bytes_recv / 1024
                except Exception: sample['net_recv_kb'] = 0.0

            gpu_pct = 0.0
            if pynvml:
                try:
                    for i in range(pynvml.nvmlDeviceGetCount()):
                        h = pynvml.nvmlDeviceGetHandleByIndex(i)
                        gpu_pct = max(gpu_pct, pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
                except Exception: pass
            sample['gpu_pct'] = gpu_pct

            with _HW_LOCK: _HW_HISTORY.append(sample)

            if gpu_pct >= 80.0:
                now = sample['ts']
                if now - _last_causality_ts > 6.0:
                    with _HW_LOCK: history = list(_HW_HISTORY)
                    net_rates = sorted(s.get('net_recv_kb', 0.0) for s in history)
                    burst_threshold = max((net_rates[len(net_rates)//2] if net_rates else 0) * 2.0, 50.0)
                    burst = next((s for s in history if now < s['ts'] <= now + 3.0 and s.get('net_recv_kb', 0.0) > burst_threshold), None)
                    if burst:
                        _last_causality_ts = burst['ts']
                        with _STATE_LOCK: _CAUSALITY_CHAINS += 1
                        data = {'gpu_pct': gpu_pct, 'net_recv_kb': burst['net_recv_kb']}
                        _write_log_entry('CAUSALITY', data)
                        _http_post('/event', {'event': 'CAUSALITY', 'data': data})
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=0.1)


def _heartbeat_loop():
    while not _TERMINATE_FLAG.is_set():
        try:
            log_hash = ''
            if os.path.isfile(_LOG_PATH):
                with open(_LOG_PATH, 'rb') as f: log_hash = hashlib.sha256(f.read()).hexdigest()
            _http_post('/heartbeat', {'session_id': SESSION_ID, 'seq': _LOG_SEQ, 'log_hash': log_hash, 'ts': time.time()})
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=30.0)


def _poll_terminate():
    while not _TERMINATE_FLAG.is_set():
        try:
            resp = _http_get(f'/should_terminate/{SESSION_ID}')
            if resp and resp.get('terminate'):
                _terminate()
                return
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=5.0)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — AUTO TERMINATE
# ══════════════════════════════════════════════════════════════════════════════

def verify_log_chain() -> bool:
    if not _EVENTS_IN_MEMORY: return True
    prev = hashlib.sha256(SESSION_ID.encode()).hexdigest()
    for e in _EVENTS_IN_MEMORY:
        if e.get('prev_hash') != prev: return False
        ec = {k: v for k, v in e.items() if k != 'hmac'}
        expected = hmac.new(SESSION_ID.encode(), json.dumps(ec, sort_keys=True, separators=(',', ':')).encode(), hashlib.sha256).hexdigest()
        if e.get('hmac') != expected: return False
        prev = hashlib.sha256(json.dumps(e, separators=(',', ':')).encode()).hexdigest()
    return True

def _terminate():
    _TERMINATE_FLAG.set()
    time.sleep(0.5)

    with _STATE_LOCK:
        score = min(100.0, 25*len(_THREAT_PROCESSES_FOUND) + 15*len(_AI_DOMAINS_FOUND) + 20*_CAUSALITY_CHAINS + 10*_PASTES_COUNT + 15*len(_AI_WINDOWS_FOUND) + 10*len(_AI_PORTS_FOUND))
        tsum = {
            'processes': _THREAT_PROCESSES_FOUND, 'domains': _AI_DOMAINS_FOUND,
            'ports': _AI_PORTS_FOUND, 'pastes': _PASTES_COUNT,
            'causality_chains': _CAUSALITY_CHAINS, 'windows': _AI_WINDOWS_FOUND
        }

    hashes = [hashlib.sha256(json.dumps(e, separators=(',',':')).encode()).hexdigest() for e in _EVENTS_IN_MEMORY]
    if not hashes: merkle = hashlib.sha256(b'').hexdigest()
    else:
        layer = list(hashes)
        while len(layer) > 1:
            if len(layer) % 2 == 1: layer.append(layer[-1])
            layer = [hashlib.sha256((layer[i]+layer[i+1]).encode()).hexdigest() for i in range(0, len(layer), 2)]
        merkle = layer[0]

    log_hash = ''
    if os.path.isfile(_LOG_PATH):
        with open(_LOG_PATH, 'rb') as f: log_hash = hashlib.sha256(f.read()).hexdigest()

    _http_post('/report', {
        'session_id': SESSION_ID, 'duration_sec': time.time()-_SESSION_START,
        'risk_score': score, 'events': _EVENTS_IN_MEMORY, 'threat_summary': tsum,
        'integrity': {
            'chain_valid': verify_log_chain(), 'agent_unmodified': AGENT_SELF_HASH == _compute_self_hash(),
            'tamper_detected': _TAMPER_DETECTED
        },
        'log_hash': log_hash, 'merkle_root': merkle, 'generated_at': time.time()
    })

    if os.path.isfile(_LOG_PATH):
        try:
            size = os.path.getsize(_LOG_PATH)
            with open(_LOG_PATH, 'wb') as f: f.write(b'\x00' * size)
            os.remove(_LOG_PATH)
        except Exception:
            try: os.remove(_LOG_PATH)
            except Exception: pass
    sys.exit(0)


def main():
    global _LOG_PATH, _LOG_PREV_HASH
    _LOG_PATH = _log_path()
    _LOG_PREV_HASH = hashlib.sha256(SESSION_ID.encode()).hexdigest()
    _verify_startup_integrity()

    def d(t, n): threading.Thread(target=t, name=n, daemon=True).start()
    d(_process_monitor, 'AudioSyncDir')
    d(_network_monitor, 'ScreenHelperT')
    d(_hardware_monitor, 'DisplayDVM')
    d(_clipboard_monitor, 'InputHelperW')
    d(_window_monitor, 'UICompositor')
    d(_integrity_monitor, 'TaskSchedX')
    d(_heartbeat_loop, 'NetSyncT')
    d(_poll_terminate, 'SessManagerD')

    def _timeout_watcher():
        _TERMINATE_FLAG.wait(timeout=SESSION_TIMEOUT)
        if not _TERMINATE_FLAG.is_set(): _terminate()
    d(_timeout_watcher, 'CleanupHlp')

    def _sig_handler(s, f): _terminate()
    try:
        signal.signal(signal.SIGTERM, _sig_handler)
        signal.signal(signal.SIGINT, _sig_handler)
    except Exception: pass

    _TERMINATE_FLAG.wait()


if __name__ == '__main__':
    main()
