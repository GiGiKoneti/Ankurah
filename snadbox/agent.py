import sys
import os
import subprocess
import time

ERROR_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent_error.log')

def log_error(msg):
    try:
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# 1. AUTO INSTALL
# ══════════════════════════════════════════════════════════════════════════════
def bootstrap():
    packages = ['psutil', 'pyperclip', 'requests', 'cryptography']
    failed = []
    
    for pkg in packages:
        try:
            __import__(pkg.split('[')[0])
            continue
        except ImportError:
            pass
            
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', pkg, '--quiet'],
            capture_output=True, text=True, timeout=60
        )
        
        try:
            __import__(pkg)
        except ImportError:
            failed.append(pkg)
            
    if failed:
        log_error(f"FATAL: FAILED TO INSTALL: {failed}")
        sys.exit(1)
        
    log_error("Bootstrap complete")

bootstrap()

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS AND GLOBALS 
# ══════════════════════════════════════════════════════════════════════════════
import requests
import psutil
import pyperclip
import threading
import uuid
import hashlib
import json

SERVER_URL = "PLACEHOLDER"
SESSION_ID = str(uuid.uuid4())
_TERMINATE_FLAG = threading.Event()

THREAT_PROCESSES = ['cluely', 'ngrok', 'ollama', 'anydesk', 'teamviewer']
AI_DOMAINS = [
    'api.openai.com', 'api.anthropic.com', 'generativelanguage.googleapis.com',
    'api.groq.com', 'api.mistral.ai', 'openrouter.ai', 'api.together.xyz',
    'parakeet-ai.com', 'interviewcoder.co', 'cluely.ai', 'ngrok.io', 'ngrok.com',
    'anydesk.com', 'teamviewer.com', 'api.cohere.com', 'huggingface.co',
    'replicate.com', 'perplexity.ai'
]
_AI_IPS_CACHE = set()  # Simplified DNS cache if needed

# ══════════════════════════════════════════════════════════════════════════════
# 2. CONNECTION VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════
def test_server_connection():
    for attempt in range(3):
        try:
            r = requests.get(f"{SERVER_URL.rstrip('/')}/health", timeout=5)
            if r.status_code == 200:
                log_error(f"Server reachable at {SERVER_URL}")
                return True
        except requests.exceptions.ConnectionError:
            log_error(f"Attempt {attempt+1}: Cannot reach {SERVER_URL}")
        except Exception as e:
            log_error(f"Attempt {attempt+1}: {e}")
        time.sleep(2)
        
    log_error(f"FATAL: Cannot connect to {SERVER_URL}")
    log_error("Check that server is running")
    log_error("Check that SERVER_URL is correct IP")
    return False


# ══════════════════════════════════════════════════════════════════════════════
# 3. REGISTER
# ══════════════════════════════════════════════════════════════════════════════
def register_with_server():
    try:
        agent_code = b""
        with open(os.path.abspath(__file__), "rb") as f:
            agent_code = f.read()
        self_hash = hashlib.sha256(agent_code).hexdigest()
        
        r = requests.post(
            f"{SERVER_URL.rstrip('/')}/register",
            json={'session_id': SESSION_ID, 'agent_hash': self_hash},
            timeout=5
        )
        if r.status_code == 200:
            log_error(f"Registered with session {SESSION_ID[:8]}")
            return True
    except Exception as e:
        log_error(f"FATAL: Register failed: {e}")
    return False


# ══════════════════════════════════════════════════════════════════════════════
# 4. GO INVISIBLE
# ══════════════════════════════════════════════════════════════════════════════
def go_invisible():
    log_error("Going invisible now")
    if sys.platform == 'win32':
        if 'pythonw' not in sys.executable.lower():
            pythonw = sys.executable.replace('python.exe', 'pythonw.exe')
            if os.path.exists(pythonw):
                subprocess.Popen(
                    [pythonw, os.path.abspath(__file__), '--invisible'], 
                    creationflags=0x08000000,
                    close_fds=True
                )
                sys.exit(0)
            
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    else:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')


# ══════════════════════════════════════════════════════════════════════════════
# 5. MONITORS
# ══════════════════════════════════════════════════════════════════════════════
def _post_event(event_type: str, data: dict):
    payload = {'session_id': SESSION_ID, 'event': event_type, 'data': data}
    try:
        requests.post(f"{SERVER_URL.rstrip('/')}/event", json=payload, headers={'X-Session-ID': SESSION_ID}, timeout=3)
    except Exception as e:
        log_error(f"Event post failed: {e}")


def thread_1_process():
    _seen_pids = set()
    while not _TERMINATE_FLAG.is_set():
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                name = (proc.info.get('name') or '').lower()
                pid = proc.pid
                if pid in _seen_pids: continue
                for threat in THREAT_PROCESSES:
                    if threat in name:
                        _seen_pids.add(pid)
                        _post_event('THREAT_PROCESS', {'name': name})
                        break
        except Exception as e:
            log_error(f"Process monitor error: {e}")
        time.sleep(3)


def thread_2_network():
    _seen_ips = set()
    while not _TERMINATE_FLAG.is_set():
        try:
            for conn in psutil.net_connections(kind='inet'):
                if not conn.raddr: continue
                ip = conn.raddr.ip
                if not ip or ip.startswith('127.') or ip == '::1' or ip in _seen_ips: continue
                
                # In simplified mode, we just resolve AI domains once periodically if needed,
                # but direct reverse DNS works here too for pure simple coverage
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                    for domain in AI_DOMAINS:
                        if hostname == domain or hostname.endswith('.' + domain):
                            _seen_ips.add(ip)
                            _post_event('AI_DOMAIN', {'domain': domain})
                            break
                except Exception:
                    pass
        except Exception as e:
            log_error(f"Network monitor error: {e}")
        time.sleep(3)


def thread_3_clipboard():
    _last_hash = ''
    while not _TERMINATE_FLAG.is_set():
        try:
            content = pyperclip.paste()
            if content and len(content) > 500:
                chash = hashlib.sha256(content.encode('utf-8', errors='replace')).hexdigest()
                if chash != _last_hash:
                    _last_hash = chash
                    _post_event('LARGE_PASTE', {'chars': len(content)})
        except Exception as e:
            log_error(f"Clipboard monitor error: {e}")
        time.sleep(1)


def thread_4_heartbeat():
    while not _TERMINATE_FLAG.is_set():
        try:
            requests.post(
                f"{SERVER_URL.rstrip('/')}/heartbeat", 
                json={'session_id': SESSION_ID, 'ts': time.time()},
                timeout=3
            )
        except Exception as e:
            log_error(f"Heartbeat failed: {e}")
        time.sleep(15)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATION
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if not test_server_connection(): sys.exit(1)
    if not register_with_server(): sys.exit(1)
    
    if '--invisible' not in sys.argv:
        go_invisible()
        
    log_error("All monitors started")
    threading.Thread(target=thread_1_process, daemon=True).start()
    threading.Thread(target=thread_2_network, daemon=True).start()
    threading.Thread(target=thread_3_clipboard, daemon=True).start()
    threading.Thread(target=thread_4_heartbeat, daemon=True).start()
    
    # Just block
    _TERMINATE_FLAG.wait()


if __name__ == '__main__':
    main()
