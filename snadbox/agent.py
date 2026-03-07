import subprocess
import sys

# ══════════════════════════════════════════════════════════════════════════════
# VERY FIRST THING — AUTO INSTALL
# ══════════════════════════════════════════════════════════════════════════════
def bootstrap():
    packages = [
        'psutil',
        'pyperclip',
        'requests',
        'cryptography'
    ]
    for pkg in packages:
        try:
            __import__(pkg.split('[')[0])
        except ImportError:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install',
                 pkg, '--quiet',
                 '--disable-pip-version-check'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    # pynvml optional
    subprocess.run(
        [sys.executable, '-m', 'pip', 'install',
         'pynvml', '--quiet'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30
    )

bootstrap()

# ══════════════════════════════════════════════════════════════════════════════
# IMMEDIATELY AFTER BOOTSTRAP — GO INVISIBLE
# ══════════════════════════════════════════════════════════════════════════════
def go_invisible():
    global sys, os, subprocess
    import os
    
    if sys.platform == 'win32':
        # Relaunch under pythonw.exe (no console)
        if 'pythonw' not in sys.executable.lower():
            pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
            if os.path.exists(pythonw):
                subprocess.Popen(
                    [pythonw, __file__] + sys.argv[1:],
                    creationflags=0x08000000,
                    close_fds=True
                )
                sys.exit(0)
    else:
        # Linux/Mac: silence all output
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    
    # Rename process
    try:
        import setproctitle  # type: ignore
        setproctitle.setproctitle('MeetHelper')
    except Exception:
        pass

go_invisible()

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS AND ENVIRONMENT
# ══════════════════════════════════════════════════════════════════════════════
import base64
import fcntl
import hashlib
import hmac
import json
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

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

sys.dont_write_bytecode = True

# ══════════════════════════════════════════════════════════════════════════════
# GLOBALS & CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
SERVER_URL = "PLACEHOLDER"
SESSION_ID = str(uuid.uuid4())

SELF_HASH = ''
HMAC_SECRET = b''
SERVER_PUBKEY = None

_LOG_PATH = ''
_LOG_LOCK = threading.Lock()
_LOG_SEQ = 0
_LOG_PREV_HASH = hashlib.sha256(SESSION_ID.encode()).hexdigest()
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
_RISK_SCORE = 0.0
_STATE_LOCK = threading.Lock()

THREAT_PROCESSES = {
    'parakeet': ('ParakeetAI', 'critical'),
    'interviewcoder': ('InterviewCoder', 'critical'),
    'shadecoder': ('ShadeCoder', 'critical'),
    'cluely': ('Cluely', 'critical'),
    'interviewsolver': ('InterviewSolver', 'critical'),
    'yoodli': ('Yoodli', 'high'),
    'ngrok': ('Tunnel', 'critical'),
    'anydesk': ('AnyDesk', 'critical'),
    'teamviewer': ('TeamViewer', 'critical'),
    'obs64': ('OBS', 'high'),
    'manycam': ('ManyCam', 'high'),
    'voicemeeter': ('VoiceMeeter', 'high'),
    'ollama': ('Ollama', 'high'),
    'lmstudio': ('LM Studio', 'high'),
    'llamafile': ('LlamaFile', 'high')
}

AI_PORTS = {11434, 1234, 8080, 7860}

AI_DOMAINS = [
    'api.openai.com', 'api.anthropic.com', 'generativelanguage.googleapis.com',
    'api.groq.com', 'api.mistral.ai', 'openrouter.ai', 'api.together.xyz',
    'parakeet-ai.com', 'interviewcoder.co', 'cluely.ai', 'ngrok.io', 'ngrok.com',
    'anydesk.com', 'teamviewer.com', 'api.cohere.com', 'huggingface.co',
    'replicate.com', 'perplexity.ai'
]

AI_WINDOW_KEYWORDS = [
    'chatgpt', 'claude', 'gemini', 'copilot', 'cluely', 'interviewcoder',
    'parakeet', 'ollama', 'perplexity', 'phind', 'bard'
]
_KW_PATTERNS = [re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE) for kw in AI_WINDOW_KEYWORDS]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _http_get(path: str) -> dict:
    if not requests: return {}
    for _ in range(2):
        try:
            r = requests.get(f"{SERVER_URL.rstrip('/')}{path}", headers={'X-Session-ID': SESSION_ID}, timeout=5)
            if r.status_code == 200: return r.json()
        except Exception: time.sleep(1)
    return {}


def _http_post(path: str, payload: dict) -> dict:
    if not requests: return {}
    for _ in range(2):
        try:
            r = requests.post(f"{SERVER_URL.rstrip('/')}{path}", json=payload, headers={'X-Session-ID': SESSION_ID}, timeout=5)
            if r.status_code == 200: return r.json()
        except Exception: time.sleep(1)
    return {}


def _update_risk(amount: int):
    global _RISK_SCORE
    with _STATE_LOCK:
        _RISK_SCORE = min(100.0, _RISK_SCORE + amount)


def log_event(event_type: str, data: dict):
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
            ser = json.dumps(entry, sort_keys=True, separators=(',', ':'))
            mac = hmac.new(HMAC_SECRET, ser.encode(), hashlib.sha256).hexdigest()
            entry['hmac'] = mac

            line = json.dumps(entry, separators=(',', ':')) + '\n'
            with open(_LOG_PATH, 'a', encoding='utf-8') as fh:
                try:
                    if sys.platform == 'win32':
                        import msvcrt
                        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                except Exception: pass
                
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
                
                try:
                    if sys.platform == 'win32':
                        import msvcrt
                        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except Exception: pass

            _LOG_PREV_HASH = hashlib.sha256(line.rstrip('\n').encode()).hexdigest()
            _LOG_SEQ += 1
            _EVENTS_IN_MEMORY.append(entry)
            
            # Post immediately
            _http_post('/event', entry)
    except Exception: pass


def _compute_self_hash() -> str:
    try:
        with open(os.path.abspath(__file__), 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception: return ''


# ══════════════════════════════════════════════════════════════════════════════
# DAEMONS
# ══════════════════════════════════════════════════════════════════════════════
def thread_1_process():
    _seen_pids, _seen_ports = set(), set()
    while not _TERMINATE_FLAG.is_set():
        try:
            if psutil:
                for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                    try:
                        name = (proc.info.get('name') or '').lower()
                        exe = (proc.info.get('exe') or '').lower()
                        pid = proc.pid
                        if pid in _seen_pids: continue
                        for threat, (friendly, level) in THREAT_PROCESSES.items():
                            if threat in name or threat in exe:
                                _seen_pids.add(pid)
                                with _STATE_LOCK:
                                    if friendly not in _THREAT_PROCESSES_FOUND:
                                        _THREAT_PROCESSES_FOUND.append(friendly)
                                _update_risk(25 if level == 'critical' else 15)
                                log_event('THREAT_PROCESS', {'name': friendly, 'match': threat, 'pid': pid})
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
                                _update_risk(10)
                                log_event('AI_PORT', {'port': port, 'pid': conn.pid, 'service': 'AI Model'})
                    except Exception: continue
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=2.0)


def thread_2_network():
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
                for conn in psutil.net_connections(kind='inet'):
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
                                    _update_risk(15)
                                    log_event('AI_DOMAIN', {'domain': domain, 'hostname': hostname})
                                break
                    except Exception: continue
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=1.0)


def thread_3_clipboard():
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
                        _update_risk(10)
                        log_event('LARGE_PASTE', {'chars': len(content), 'hash': chash})
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=0.2)


def thread_4_window():
    _seen_windows = set()
    while not _TERMINATE_FLAG.is_set():
        try:
            titles = []
            if sys.platform == 'win32':
                import ctypes, ctypes.wintypes
                _t = []
                def _cb(hwnd, _):
                    try:
                        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buf = ctypes.create_unicode_buffer(length + 1)
                            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                            if buf.value.strip(): _t.append(buf.value)
                    except Exception: pass
                    return True
                EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
                ctypes.windll.user32.EnumWindows(EnumProc(_cb), 0)
                titles = _t
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

            for title in titles:
                for i, pattern in enumerate(_KW_PATTERNS):
                    kw = AI_WINDOW_KEYWORDS[i]
                    if pattern.search(title):
                        key = f'{kw}:{title[:50]}'
                        if key not in _seen_windows:
                            _seen_windows.add(key)
                            with _STATE_LOCK:
                                if kw not in _AI_WINDOWS_FOUND: _AI_WINDOWS_FOUND.append(kw)
                            _update_risk(15)
                            log_event('AI_WINDOW', {'keyword': kw, 'title': title[:50]})
                        break
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=1.0)


def thread_5_hardware():
    global _CAUSALITY_CHAINS
    _last_causality_ts = 0.0
    while not _TERMINATE_FLAG.is_set():
        try:
            sample = {'ts': time.time(), 'cpu_pct': 0.0, 'ram_gb': 0.0, 'net_recv_kb': 0.0, 'gpu_pct': 0.0}
            if psutil:
                try: sample['cpu_pct'] = psutil.cpu_percent()
                except Exception: pass
                try: sample['ram_gb'] = psutil.virtual_memory().used / 1e9
                except Exception: pass
                try: sample['net_recv_kb'] = psutil.net_io_counters().bytes_recv / 1024
                except Exception: pass
            if pynvml:
                try:
                    for i in range(pynvml.nvmlDeviceGetCount()):
                        h = pynvml.nvmlDeviceGetHandleByIndex(i)
                        sample['gpu_pct'] = max(sample['gpu_pct'], pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
                except Exception: pass

            with _HW_LOCK: _HW_HISTORY.append(sample)

            if sample['gpu_pct'] >= 80.0:
                now = sample['ts']
                if now - _last_causality_ts > 6.0:
                    with _HW_LOCK: history = list(_HW_HISTORY)
                    net_rates = sorted(s['net_recv_kb'] for s in history)
                    if net_rates:
                        median = net_rates[len(net_rates)//2]
                        if next((s for s in history if now < s['ts'] <= now + 3.0 and s['net_recv_kb'] > max(median * 2.0, 50.0)), None):
                            _last_causality_ts = now
                            with _STATE_LOCK: _CAUSALITY_CHAINS += 1
                            _update_risk(20)
                            log_event('CAUSALITY', {'gpu_pct': sample['gpu_pct']})
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=0.1)


def thread_6_integrity():
    global _TAMPER_DETECTED
    while not _TERMINATE_FLAG.is_set():
        try:
            time.sleep(60)
            if _compute_self_hash() != SELF_HASH:
                with _STATE_LOCK: _TAMPER_DETECTED = True
                _update_risk(30)
                log_event('TAMPER', {'desc': 'Self-hash mismatch'})
        except Exception: pass


def thread_7_heartbeat():
    while not _TERMINATE_FLAG.is_set():
        try:
            log_h = ''
            if os.path.isfile(_LOG_PATH):
                with open(_LOG_PATH, 'rb') as f: log_h = hashlib.sha256(f.read()).hexdigest()
            payload = {'session_id': SESSION_ID, 'seq': _LOG_SEQ, 'log_hash': log_h, 'ts': time.time()}
            ser = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            payload['hmac'] = hmac.new(HMAC_SECRET, ser.encode(), hashlib.sha256).hexdigest()
            _http_post('/heartbeat', payload)
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=30.0)


def thread_8_poller():
    while not _TERMINATE_FLAG.is_set():
        try:
            if _http_get(f'/should_terminate/{SESSION_ID}').get('terminate'):
                shutdown()
                return
        except Exception: pass
        _TERMINATE_FLAG.wait(timeout=5.0)


# ══════════════════════════════════════════════════════════════════════════════
# STARTUP & SHUTDOWN
# ══════════════════════════════════════════════════════════════════════════════
def verify_log_chain() -> bool:
    if not _EVENTS_IN_MEMORY: return True
    prev = hashlib.sha256(SESSION_ID.encode()).hexdigest()
    for e in _EVENTS_IN_MEMORY:
        if e.get('prev_hash') != prev: return False
        ec = {k: v for k, v in e.items() if k != 'hmac'}
        expected = hmac.new(HMAC_SECRET, json.dumps(ec, sort_keys=True, separators=(',', ':')).encode(), hashlib.sha256).hexdigest()
        if e.get('hmac') != expected: return False
        prev = hashlib.sha256(json.dumps(e, separators=(',', ':')).encode()).hexdigest()
    return True


def shutdown():
    _TERMINATE_FLAG.set()
    time.sleep(0.5)

    log_event('SESSION_END', {'desc': 'Termination triggered'})

    # Build report
    hashes_list = [hashlib.sha256(json.dumps(e, separators=(',',':')).encode()).hexdigest() for e in _EVENTS_IN_MEMORY]
    if not hashes_list: merkle = hashlib.sha256(b'').hexdigest()
    else:
        layer = list(hashes_list)
        while len(layer) > 1:
            if len(layer) % 2 == 1: layer.append(layer[-1])
            layer = [hashlib.sha256((layer[i]+layer[i+1]).encode()).hexdigest() for i in range(0, len(layer), 2)]
        merkle = layer[0]

    log_h = ''
    if os.path.isfile(_LOG_PATH):
        with open(_LOG_PATH, 'rb') as f: log_h = hashlib.sha256(f.read()).hexdigest()

    report = {
        'session_id': SESSION_ID,
        'duration_sec': time.time() - _SESSION_START,
        'risk_score': min(100.0, _RISK_SCORE),
        'events': _EVENTS_IN_MEMORY,
        'threat_summary': {
            'processes': _THREAT_PROCESSES_FOUND,
            'domains': _AI_DOMAINS_FOUND,
            'ports': _AI_PORTS_FOUND,
            'paste_count': _PASTES_COUNT,
            'causality_count': _CAUSALITY_CHAINS,
            'windows': _AI_WINDOWS_FOUND
        },
        'integrity': {
            'chain_valid': verify_log_chain(),
            'agent_unmodified': SELF_HASH == _compute_self_hash(),
            'tamper_detected': _TAMPER_DETECTED
        },
        'merkle_root': merkle,
        'log_hash': log_h,
        'agent_hash': SELF_HASH,
        'generated_at': time.time()
    }

    # Sign Report
    sig_payload = f"{merkle}:{SESSION_ID}:{report['generated_at']}"
    report['signature'] = hmac.new(HMAC_SECRET, sig_payload.encode(), hashlib.sha256).hexdigest()

    # Encrypt with Server public key
    report_json = json.dumps(report).encode()
    if SERVER_PUBKEY:
        encrypted = SERVER_PUBKEY.encrypt(
            report_json,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        _http_post('/report', {'encrypted_payload': base64.b64encode(encrypted).decode('utf-8')})

    # Delete log
    if os.path.isfile(_LOG_PATH):
        try:
            sz = os.path.getsize(_LOG_PATH)
            with open(_LOG_PATH, 'wb') as f: f.write(b'\x00' * sz)
            os.remove(_LOG_PATH)
        except Exception:
            try: os.remove(_LOG_PATH)
            except Exception: pass

    sys.exit(0)


def main():
    global SELF_HASH, HMAC_SECRET, SERVER_PUBKEY, _LOG_PATH
    
    # 1. Compute self hash
    SELF_HASH = _compute_self_hash()
    
    # 2. Fetch server authorized agent hash
    auth = _http_get('/agent/hash')
    if auth.get('hash') and auth.get('hash') != SELF_HASH:
        _http_post('/event', {'event': 'TAMPER', 'data': {'desc': 'Agent signature unrecognised by server'}})
        sys.exit(1)
        
    # 3. Fetch HMAC secret
    sec = _http_get(f'/agent/hmac-secret/{SESSION_ID}')
    if sec and sec.get('secret'):
        HMAC_SECRET = sec['secret'].encode('utf-8')
    else:
        HMAC_SECRET = b'fallback'
        
    # Fetch public key for encrypted report
    pk = _http_get('/agent/public_key')
    if pk and pk.get('key'):
        SERVER_PUBKEY = load_pem_public_key(pk['key'].encode('utf-8'))
        
    # 4. Register
    _http_post('/register', {'session_id': SESSION_ID, 'agent_hash': SELF_HASH})

    # 5. Set log file path
    short_id = SESSION_ID[:8]
    if sys.platform == 'win32':
        tmp = os.environ.get('TEMP', os.environ.get('TMP', 'C:\\Temp'))
        _LOG_PATH = os.path.join(tmp, f'mh_{short_id}.tmp')
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(_LOG_PATH, 2)
        except Exception: pass
    else:
        _LOG_PATH = f'/tmp/.mh_{short_id}'
        
    # 6 & 7. Start threads
    def d(t): threading.Thread(target=t, daemon=True).start()
    d(thread_1_process)
    d(thread_2_network)
    d(thread_3_clipboard)
    d(thread_4_window)
    d(thread_5_hardware)
    d(thread_6_integrity)
    d(thread_7_heartbeat)
    d(thread_8_poller)

    # Watchdog timeout
    try:
        signal.signal(signal.SIGTERM, lambda s, f: shutdown())
        signal.signal(signal.SIGINT, lambda s, f: shutdown())
    except Exception: pass

    while not _TERMINATE_FLAG.is_set():
        if time.time() - _SESSION_START > 10800:
            shutdown()
        time.sleep(1)


if __name__ == '__main__':
    main()
