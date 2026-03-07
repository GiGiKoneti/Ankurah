# INTERVIEWER SETUP:
# 1. python server.py
# 2. That's it. Copy the launcher command shown and send to candidate.

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — AUTO INSTALL
# ══════════════════════════════════════════════════════════════════════════════
def _bootstrap():
    import subprocess, sys
    REQUIRED = ['fastapi', 'uvicorn', 'cryptography', 'requests']
    
    try: import pip
    except ImportError:
        subprocess.run([sys.executable, '-m', 'ensurepip', '--quiet'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for pkg in REQUIRED:
        try: __import__(pkg)
        except ImportError:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', pkg, '--quiet', '--disable-pip-version-check'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

_bootstrap()

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS AND CONFIG
# ══════════════════════════════════════════════════════════════════════════════
import argparse
import datetime
import hashlib
import hmac
import json
import os
import socket
import sys
import threading
import time
from typing import Any, Dict
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 & 3 — AUTO FIND IP AND OPEN FIREWALL
# ══════════════════════════════════════════════════════════════════════════════
def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def open_firewall():
    if sys.platform == 'win32':
        import subprocess
        subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            'name=TruthLens', 'dir=in', 'action=allow', 
            'protocol=TCP', 'localport=8000'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ══════════════════════════════════════════════════════════════════════════════
# STATE & HELPERS
# ══════════════════════════════════════════════════════════════════════════════
SERVER_PORT = 8000
LOCAL_IP = get_local_ip()
HEARTBEAT_GRACE = 60.0

_RESET  = '\033[0m'
_BOLD   = '\033[1m'
_RED    = '\033[91m'
_YELLOW = '\033[93m'
_GREEN  = '\033[92m'
_CYAN   = '\033[96m'

_sessions: Dict[str, Dict[str, Any]] = {}

def _get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in _sessions:
        _sessions[session_id] = {
            'session_id': session_id,
            'last_heartbeat': time.time(),
            'authorized_hash': '',
            'terminate_flag': False,
        }
    return _sessions[session_id]


def _format_ts(ts: float = 0) -> str:
    if not ts: ts = time.time()
    return datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')

def _print_report(report: Dict) -> None:
    session_id  = report.get('session_id', 'N/A')
    duration    = report.get('duration_sec', 0)
    score       = report.get('risk_score', 0)
    integrity   = report.get('integrity', {})
    events      = report.get('events', [])
    threat_sum  = report.get('threat_summary', {})
    merkle      = report.get('merkle_root', '')

    dur_min = int(duration // 60)
    dur_sec = int(duration % 60)

    if score >= 86: emoji = f"{_RED}{_BOLD}💀 CRITICAL{_RESET}"
    elif score >= 61: emoji = f"{_RED}{_BOLD}🔴 HIGH RISK{_RESET}"
    elif score >= 31: emoji = f"{_YELLOW}{_BOLD}🟡 MEDIUM RISK{_RESET}"
    else: emoji = f"{_GREEN}{_BOLD}✅ LOW RISK{_RESET}"

    w = 54
    bar = '═' * w
    def _line(text: str = '') -> str: return f'║ {text:<{w - 2}}║'
    def _yes_no(val: bool) -> str: return f"{_GREEN}yes{_RESET}" if val else f"{_RED}no{_RESET}"

    print(f'\n╔{bar}╗')
    print(f'║{" " * 15}{_BOLD}TRUTHLENS SESSION REPORT{" " * 15}{_RESET}║')
    print(f'╠{bar}╣')
    print(_line(f'Session:    {session_id[:8]}'))
    print(_line(f'Duration:   {dur_min}m {dur_sec}s'))
    print(f'║ Risk Score: {score:.0f}/100  {emoji:<{w + 5}}║')
    print(f'╠{bar}╣')
    print(_line(f'{_BOLD}INTEGRITY{_RESET}'))
    print(f'║  Chain valid:      {_yes_no(integrity.get("chain_valid", False)):<{w + 7}}║')
    print(f'║  Agent unmodified: {_yes_no(integrity.get("agent_unmodified", False)):<{w + 7}}║')
    print(f'║  Tamper detected:  {_yes_no(not integrity.get("tamper_detected", False)):<{w + 7}}║')
    print(f'╠{bar}╣')
    print(_line(f'{_BOLD}THREAT SUMMARY{_RESET}'))
    
    procs = ', '.join(threat_sum.get("processes", [])) or "None"
    doms  = ', '.join(threat_sum.get("domains", [])) or "None"
    if len(procs) > w - 16: procs = procs[:w - 19] + '...'
    if len(doms) > w - 16:  doms = doms[:w - 18] + '...'

    print(_line(f'  Processes:   {procs}'))
    print(_line(f'  AI Domains:  {doms}'))
    print(_line(f'  Pastes:      {threat_sum.get("pastes", 0)}'))
    print(_line(f'  Causality:   {threat_sum.get("causality_chains", 0)}'))
    print(f'╠{bar}╣')
    print(_line(f'{_BOLD}TIMELINE{_RESET}'))

    if not events:
        print(_line('  (no events)'))
    else:
        for entry in events[:20]:
            ts_str = _format_ts(entry.get('ts', 0))
            ev     = entry.get('event', '')
            data   = entry.get('data', {})

            if ev == 'THREAT_PROCESS': desc = f"{data.get('name', '')} ({data.get('match', '')})"
            elif ev == 'AI_DOMAIN': desc = f"{data.get('domain', '')}"
            elif ev == 'CAUSALITY': desc = f"GPU {data.get('gpu_pct', 0):.0f}% → net burst"
            elif ev == 'LARGE_PASTE': desc = f"{data.get('char_count', 0)} chars"
            elif ev == 'AI_WINDOW': desc = f"'{data.get('keyword', '')}' in title"
            elif ev == 'AI_PORT': desc = f"port {data.get('port', '')}"
            elif ev == 'TAMPER': desc = f"{data.get('desc', 'Unknown')}"
            else: desc = ""

            line_str = f'  {ts_str}  {ev[:14]:<14} {desc}'
            if len(line_str) > w - 2: line_str = line_str[:w - 5] + '...'
            print(_line(line_str))
        if len(events) > 20: print(_line(f'  ... and {len(events) - 20} more events ...'))

    print(f'╠{bar}╣')
    print(_line(f'Merkle Root: {merkle[:38]}...'))
    print(f'╚{bar}╝\n')

# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ══════════════════════════════════════════════════════════════════════════════
app = FastAPI(title='TruthLens Integrity Server', docs_url=None, redoc_url=None)

@app.post('/register')
async def post_register(request: Request):
    body = await request.json()
    session_id = body.get('session_id', '')
    agent_hash = body.get('hash', '')
    sess = _get_session(session_id)
    sess['authorized_hash'] = agent_hash
    print(f"[{_format_ts()}] {_GREEN}Agent connected — session {session_id[:8]}{_RESET}")
    return {'ok': True}

@app.post('/event')
async def post_event(request: Request):
    body = await request.json()
    session_id = request.headers.get('x-session-id', 'Unknown')
    
    if 'hmac' in body:
        ec = {k: v for k, v in body.items() if k != 'hmac'}
        ser = json.dumps(ec, sort_keys=True, separators=(',', ':'))
        expect = hmac.new(session_id.encode(), ser.encode(), hashlib.sha256).hexdigest()
        if expect != body['hmac']:
            print(f"[{_format_ts()}] {_YELLOW}⚠️  INVALID HMAC on event from session {session_id[:8]}{_RESET}")

    ev   = body.get('event', '')
    data = body.get('data', {})

    if ev == 'THREAT_PROCESS': print(f"[{_format_ts()}] {_RED}{_BOLD}💀 CRITICAL:{_RESET} {data.get('name', 'Process')} detected")
    elif ev == 'AI_DOMAIN': print(f"[{_format_ts()}] {_RED}🔴 AI API:{_RESET} {data.get('domain', 'Domain')} connected")
    elif ev == 'AI_PORT': print(f"[{_format_ts()}] {_YELLOW}⚠️  AI PORT:{_RESET} {data.get('port', '')} listening")
    elif ev == 'LARGE_PASTE': print(f"[{_format_ts()}] {_CYAN}📋 PASTE:{_RESET} {data.get('char_count', 0)} chars")
    elif ev == 'AI_WINDOW': print(f"[{_format_ts()}] {_YELLOW}👁️  WINDOW:{_RESET} {data.get('title', '')}")
    elif ev == 'CAUSALITY': print(f"[{_format_ts()}] {_RED}{_BOLD}⚡ CAUSALITY CHAIN FIRED{_RESET}")
    elif ev == 'TAMPER': print(f"[{_format_ts()}] {_RED}{_BOLD}🚨 TAMPER DETECTED{_RESET}")

    return {'ok': True}

@app.post('/heartbeat')
async def post_heartbeat(request: Request):
    body = await request.json()
    sess = _get_session(body.get('session_id', ''))
    sess['last_heartbeat'] = time.time()
    return {'ok': True}

@app.post('/report')
async def post_report(request: Request):
    report = await request.json()
    _print_report(report)
    return {'ok': True}

@app.get('/should_terminate/{session_id}')
def get_terminate(session_id: str):
    sess = _get_session(session_id)
    if sess['terminate_flag']:
        print(f"[{_format_ts()}] {_CYAN}🛑  Termination signal pulled by session {session_id[:8]}{_RESET}")
    return {'terminate': sess['terminate_flag']}

# Add a manual trigger if interviewer wants to terminate them from server
@app.get('/terminate/{session_id}')
def set_terminate(session_id: str):
    sess = _get_session(session_id)
    sess['terminate_flag'] = True
    print(f"[{_format_ts()}] {_CYAN}🛑  Termination scheduled for session {session_id[:8]}{_RESET}")
    return {'ok': True}

@app.get('/status')
def get_status():
    active = {}
    for sid, sess in _sessions.items():
        active[sid] = {'last_heartbeat': sess['last_heartbeat'], 'age_seconds': time.time() - sess['last_heartbeat']}
    return {'active_sessions': active}

# STEP 5 — SERVE AGENT FILE
@app.get('/agent/truthlens_agent.py', response_class=PlainTextResponse)
def get_agent_file():
    agent_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'truthlens_agent.py')
    if not os.path.exists(agent_path):
        return f"# Error: truthlens_agent.py not found at {agent_path}"
    
    with open(agent_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Auto-inject the server IP so Candidate doesn't have to edit the file
    content = content.replace("REPLACE_WITH_YOUR_IP", LOCAL_IP)
    return content

# ══════════════════════════════════════════════════════════════════════════════
# WATCHDOG
# ══════════════════════════════════════════════════════════════════════════════
def _heartbeat_watchdog():
    while True:
        try:
            time.sleep(15)
            now = time.time()
            for session_id, sess in list(_sessions.items()):
                if now - sess.get('last_heartbeat', now) > HEARTBEAT_GRACE:
                    print(f"[{_format_ts(now)}] {_RED}{_BOLD}❌ HEARTBEAT LOST{_RESET} — possible agent termination (session {session_id[:8]})")
        except Exception: pass

threading.Thread(target=_heartbeat_watchdog, name='watchdog', daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
# STARTUP BANNER
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    open_firewall()
    
    print(f"""
╔══════════════════════════════════════════╗
║     TRUTHLENS SERVER STARTED             ║
║     Your IP: {LOCAL_IP:<27} ║
║     Port: 8000                           ║
║                                          ║
║     Edit agent SERVER_URL to:            ║
║     http://{LOCAL_IP}:8000{" "*(21-len(LOCAL_IP))} ║
║                                          ║  
║     Waiting for agents...                ║
╚══════════════════════════════════════════╝

{_BOLD}SEND THIS TO FRIEND:{_RESET}
─────────────────────────────────────────
Windows: Save as run.bat and double click
@echo off
curl -s http://{LOCAL_IP}:8000/agent/truthlens_agent.py -o %TEMP%\\agent.py && pip install psutil pyperclip pynvml requests cryptography -q && pythonw %TEMP%\\agent.py
─────────────────────────────────────────
Linux/Mac: run this command:
curl -s http://{LOCAL_IP}:8000/agent/truthlens_agent.py | python3 -
─────────────────────────────────────────
""")

    uvicorn.run(app, host='0.0.0.0', port=SERVER_PORT, log_level='warning')
