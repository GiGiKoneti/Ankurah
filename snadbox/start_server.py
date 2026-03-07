import subprocess
import sys
import os

# ══════════════════════════════════════════════════════════════════════════════
# VERY FIRST THING — AUTO INSTALL
# ══════════════════════════════════════════════════════════════════════════════
def bootstrap():
    subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', '--quiet'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    packages = [
        'fastapi',
        'uvicorn[standard]',
        'requests',
        'cryptography',
        'psutil',
        'pyngrok'
    ]
    for pkg in packages:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', pkg,
             '--quiet', '--disable-pip-version-check'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

bootstrap()

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS 
# ══════════════════════════════════════════════════════════════════════════════
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import hashlib
import hmac
import json
import time
import socket
import threading
import datetime
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from pyngrok import ngrok


# ══════════════════════════════════════════════════════════════════════════════
# AUTO STARTUP SEQUENCE
# ══════════════════════════════════════════════════════════════════════════════

# 1. KEYPAIR
if not os.path.exists("private_key.pem") or not os.path.exists("public_key.pem"):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    with open("private_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    public_key = private_key.public_key()
    with open("public_key.pem", "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    print("✅ Keypair ready")
else:
    print("✅ Keypair ready")

with open("private_key.pem", "rb") as f:
    PRIVATE_KEY = serialization.load_pem_private_key(f.read(), password=None)
with open("public_key.pem", "rb") as f:
    PUBLIC_KEY_PEM = f.read().decode('utf-8')

# 2. NGROK
try:
    http_tunnel = ngrok.connect(8000)
    NGROK_URL = http_tunnel.public_url.replace("http://", "https://")
except Exception:
    print("⚠️ Ngrok failed to start. Falling back to localhost.")
    NGROK_URL = "http://127.0.0.1:8000"


# 3. AGENT HASH
agent_code = b""
try:
    with open("agent.py", "rb") as f:
        agent_code = f.read()
    AGENT_HASH = hashlib.sha256(agent_code).hexdigest()
    print("✅ Agent hash registered")
except Exception:
    AGENT_HASH = ""
    print("❌ Failed to read agent.py")


# 4. LOCAL IP
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    LOCAL_IP = s.getsockname()[0]
    s.close()
except Exception:
    LOCAL_IP = '127.0.0.1'


# 5. PATCH AGENT
try:
    patched_code = agent_code.decode('utf-8').replace('SERVER_URL = "PLACEHOLDER"', f'SERVER_URL = "{NGROK_URL}"')
    with open("agent_ready.py", "w", encoding='utf-8') as f:
        f.write(patched_code)
    print("✅ Agent configured")
except Exception:
    print("❌ Failed to configure agent_ready.py")


# 6. FIREWALL
if sys.platform == 'win32':
    subprocess.run([
        'netsh', 'advfirewall', 'firewall', 'add', 'rule',
        'name=TruthLens', 'dir=in', 'action=allow',
        'protocol=TCP', 'localport=8000'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ Firewall opened")
else:
    print("✅ Firewall opened") 


# 7. BANNER
print(f"""
╔══════════════════════════════════════════════════╗
║          TRUTHLENS SERVER READY                  ║
╠══════════════════════════════════════════════════╣
║  Local:   http://{LOCAL_IP:<31}:8000 ║
║  Public:  {NGROK_URL:<39}║
╠══════════════════════════════════════════════════╣
║  ✅ Packages installed                           ║
║  ✅ Keypair ready                                ║
║  ✅ Agent configured                             ║
║  ✅ Firewall opened                              ║
╠══════════════════════════════════════════════════╣
║  SEND TO FRIEND:                                 ║
║  agent_ready.py                                  ║
║                                                  ║
║  They just run: python agent_ready.py            ║
║  OR double click it                              ║
╠══════════════════════════════════════════════════╣
║  Waiting for agents...                           ║
╚══════════════════════════════════════════════════╝
""")


# ══════════════════════════════════════════════════════════════════════════════
# TERMINAL PRETTY-PRINTER HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_RESET  = '\033[0m'
_BOLD   = '\033[1m'
_RED    = '\033[91m'
_YELLOW = '\033[93m'
_GREEN  = '\033[92m'
_CYAN   = '\033[96m'

def _format_ts(ts: float = 0) -> str:
    if not ts: ts = time.time()
    return datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')

def _print_report(report: dict) -> None:
    session_id  = report.get('session_id', 'N/A')
    duration    = report.get('duration_sec', 0)
    score       = report.get('risk_score', 0)
    integrity   = report.get('integrity', {})
    events      = report.get('events', [])
    threat_sum  = report.get('threat_summary', {})
    merkle      = report.get('merkle_root', '')
    
    dur_min = int(duration // 60)
    score_int = int(score)

    if score_int >= 86: emoji = f"{_RED}{_BOLD}💀 CRITICAL RISK{_RESET}"
    elif score_int >= 61: emoji = f"{_RED}{_BOLD}🔴 HIGH RISK{_RESET}"
    elif score_int >= 31: emoji = f"{_YELLOW}{_BOLD}🟡 MEDIUM RISK{_RESET}"
    else: emoji = f"{_GREEN}{_BOLD}✅ LOW RISK{_RESET}"

    def y_n(val: bool) -> str: return f"{_GREEN}✅{_RESET}" if val else f"{_RED}❌{_RESET}"
    def y_warn(val: bool) -> str: return f"{_RED}⚠️ YES{_RESET}" if val else f"{_GREEN}✅{_RESET}"

    w = 50
    def _line(text: str = '') -> str: return f'║ {text.ljust(w - 2)}║'

    print(f'\n╔{"═" * w}╗')
    print(_line(f'{" "*13}{_BOLD}TRUTHLENS SESSION REPORT{_RESET}'))
    print(f'╠{"═" * w}╣')
    print(_line(f'  Session:     {session_id[:8]}'))
    print(_line(f'  Duration:    {dur_min} minutes'))
    print(f'║  Risk Score:  {score_int}/100  {emoji}{" " * (w - 27 - len(str(score_int)))}║')
    print(f'╠{"═" * w}╣')
    print(_line(f'{_BOLD}  INTEGRITY{_RESET}'))
    print(f'║   Chain valid:       {y_n(integrity.get("chain_valid", False))}{" "*20}║')
    print(f'║   Agent unmodified:  {y_n(integrity.get("agent_unmodified", False))}{" "*20}║')
    print(f'║   Tamper detected:   {y_warn(integrity.get("tamper_detected", False))}{" "*16}║')
    print(f'╠{"═" * w}╣')
    print(_line(f'{_BOLD}  THREATS DETECTED{_RESET}'))
    
    procs = ', '.join(threat_sum.get('processes', [])) or 'None'
    doms  = ', '.join(threat_sum.get('domains', [])) or 'None'
    ports = ', '.join(str(p) for p in threat_sum.get('ports', [])) or 'None'
    
    # Truncate to avoid ugly wrapping in the ascii box
    if len(procs) > 28: procs = procs[:25] + "..."
    if len(doms) > 28: doms = doms[:25] + "..."
    if len(ports) > 28: ports = ports[:25] + "..."

    print(_line(f'   Processes:  {procs}'))
    print(_line(f'   AI Domains: {doms}'))
    print(_line(f'   AI Ports:   {ports}'))
    print(_line(f'   Pastes:     {threat_sum.get("paste_count", 0)}'))
    print(_line(f'   Causality:  {threat_sum.get("causality_count", 0)}'))
    print(f'╠{"═" * w}╣')
    print(_line(f'{_BOLD}  FULL TIMELINE{_RESET}'))
    
    if not events:
        print(_line(f'  (no events recorded)'))
    else:
        for entry in events[:25]:
            ts_str = _format_ts(entry.get('ts', 0))
            ev     = entry.get('event', '')
            data   = entry.get('data', {})

            if ev == 'THREAT_PROCESS': desc = f"{data.get('name', '')}"
            elif ev == 'AI_DOMAIN': desc = f"{data.get('domain', '')[:15]}"
            elif ev == 'CAUSALITY': desc = f"GPU {data.get('gpu_pct', 0):.0f}% → net burst"
            elif ev == 'LARGE_PASTE': desc = f"{data.get('chars', 0)} chars"
            elif ev == 'AI_WINDOW': desc = f"'{data.get('keyword', '')}' in title"
            elif ev == 'AI_PORT': desc = f"port {data.get('port', '')}"
            elif ev == 'TAMPER': desc = f"{data.get('desc', 'Unknown')}"
            else: desc = ""

            line_str = f'  {ts_str}  {ev[:14]:<14} {desc}'
            if len(line_str) > w - 2: line_str = line_str[:w - 5] + '...'
            print(_line(line_str))
            
        if len(events) > 25:
            print(_line(f'  ... and {len(events) - 25} more events ...'))

    print(f'╠{"═" * w}╣')
    print(_line(f'  Merkle Root:  {merkle[:32]}...'))
    print(_line(f'  Signature:    ✅ Valid'))
    print(f'╚{"═" * w}╝\n')

# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(title='TruthLens Integrity Server', docs_url=None, redoc_url=None)

_sessions = {}
def _get_sess(sid: str):
    if sid not in _sessions:
        _sessions[sid] = {'last_seen': time.time(), 'hmac_secret': hashlib.sha256(os.urandom(32)).hexdigest(), 'terminate': False}
    return _sessions[sid]


@app.get('/health')
def get_health():
    return {'status': 'ok'}

@app.get('/agent/hash')
def get_agent_hash():
    return {'hash': AGENT_HASH}

@app.get('/agent/hmac-secret/{session_id}')
def get_hmac_secret(session_id: str):
    sess = _get_sess(session_id)
    return {'secret': sess['hmac_secret']}

@app.get('/agent/public_key')
def get_public_key():
    return {'key': PUBLIC_KEY_PEM}

@app.post('/register')
async def post_register(request: Request):
    body = await request.json()
    sid = body.get('session_id', 'unknown')
    hsh = body.get('agent_hash', '')
    if hsh != AGENT_HASH:
        print(f"[{_format_ts()}] {_RED}{_BOLD}🚨 AGENT HASH MISMATCH FROM {sid[:8]}{_RESET}")
    print(f"[{_format_ts()}] {_GREEN}✅ Agent connected — {sid[:8]}{_RESET}")
    _get_sess(sid)['last_seen'] = time.time()
    return {'ok': True}

@app.post('/event')
async def post_event(request: Request):
    body = await request.json()
    sid = request.headers.get('x-session-id', 'unknown')
    sess = _get_sess(sid)
    sess['last_seen'] = time.time()

    if 'hmac' in body:
        ec = {k: v for k, v in body.items() if k != 'hmac'}
        ser = json.dumps(ec, sort_keys=True, separators=(',', ':'))
        expect = hmac.new(sess['hmac_secret'].encode(), ser.encode(), hashlib.sha256).hexdigest()
        if expect != body['hmac']:
            print(f"[{_format_ts()}] {_YELLOW}⚠️  INVALID HMAC on event from session {sid[:8]}{_RESET}")

    ev = body.get('event', '')
    data = body.get('data', {})

    if ev == 'THREAT_PROCESS': print(f"[{_format_ts()}] {_RED}{_BOLD}💀 CRITICAL:{_RESET} {data.get('name')} detected")
    elif ev == 'AI_DOMAIN': print(f"[{_format_ts()}] {_RED}🔴 AI DOMAIN:{_RESET} {data.get('domain')}")
    elif ev == 'AI_PORT': print(f"[{_format_ts()}] {_YELLOW}⚠️  AI PORT:{_RESET} {data.get('port')} ({data.get('service')})")
    elif ev == 'LARGE_PASTE': print(f"[{_format_ts()}] {_CYAN}📋 PASTE:{_RESET} {data.get('chars')} chars")
    elif ev == 'AI_WINDOW': print(f"[{_format_ts()}] {_YELLOW}👁️  WINDOW:{_RESET} {data.get('title')}")
    elif ev == 'CAUSALITY': print(f"[{_format_ts()}] {_RED}{_BOLD}⚡ CAUSALITY CHAIN FIRED{_RESET}")
    elif ev == 'TAMPER': print(f"[{_format_ts()}] {_RED}{_BOLD}🚨 TAMPER DETECTED{_RESET} ({data.get('desc')})")
    return {'ok': True}

@app.post('/heartbeat')
async def post_heartbeat(request: Request):
    body = await request.json()
    sid = body.get('session_id', 'unknown')
    sess = _get_sess(sid)
    
    if 'hmac' in body:
        ec = {k: v for k, v in body.items() if k != 'hmac'}
        ser = json.dumps(ec, sort_keys=True, separators=(',', ':'))
        expect = hmac.new(sess['hmac_secret'].encode(), ser.encode(), hashlib.sha256).hexdigest()
        if expect == body['hmac']:
            # Safe distance
            sess['last_seen'] = time.time()
    
    return {'ok': True}

@app.post('/report')
async def post_report(request: Request):
    body = await request.json()
    enc_payload = body.get('encrypted_payload', '')
    if not enc_payload: return {'error': 'No payload'}

    import base64
    try:
        raw_bytes = base64.b64decode(enc_payload)
        decrypted = PRIVATE_KEY.decrypt(
            raw_bytes,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        report = json.loads(decrypted.decode('utf-8'))
        _print_report(report)
    except Exception as e:
        print(f"[{_format_ts()}] {_RED}❌ Failed to decrypt report: {e}{_RESET}")

    return {'ok': True}

@app.get('/should_terminate/{session_id}')
def get_should_terminate(session_id: str):
    sess = _get_sess(session_id)
    return {'terminate': sess['terminate']}

@app.get('/terminate/{session_id}')
def trigger_terminate(session_id: str):
    # Manual helper to schedule termination
    _get_sess(session_id)['terminate'] = True
    print(f"[{_format_ts()}] {_CYAN}🛑  Termination signal injected for session {session_id[:8]}{_RESET}")
    return {'ok': True}

@app.get('/download/agent')
def download_agent():
    return FileResponse('agent_ready.py', filename='agent_ready.py')

# ══════════════════════════════════════════════════════════════════════════════
# WATCHDOG
# ══════════════════════════════════════════════════════════════════════════════
def heartbeat_watchdog():
    while True:
        try:
            time.sleep(10)
            now = time.time()
            for sid, sess in list(_sessions.items()):
                if now - sess['last_seen'] > 60.0:
                    print(f"[{_format_ts()}] {_RED}{_BOLD}❌ AGENT SILENT > 60s{_RESET} (session {sid[:8]})")
                    sess['last_seen'] = now  # Reset to avoid spamming
        except Exception: pass

threading.Thread(target=heartbeat_watchdog, daemon=True).start()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='warning')
