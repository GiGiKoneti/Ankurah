import re
import os

BASE_DIR = '/home/bitwisebrain/snadbox/ai_detector'

# 1. config.py
with open(f'{BASE_DIR}/config.py', 'r') as f:
    config = f.read()

config = re.sub(r'RAM_SPIKE_MB\s*=\s*500', 'RAM_SPIKE_MB          = 2000', config)
config = re.sub(r'RAM_LLM_THRESHOLD_GB\s*=\s*4\.0', 'RAM_LLM_THRESHOLD_GB  = 5.0', config)
config = re.sub(r'GPU_UTIL_THRESHOLD\s*=\s*30', 'GPU_UTIL_THRESHOLD    = 50', config)
config = re.sub(r'GPU_SPIKE_THRESHOLD\s*=\s*70', 'GPU_SPIKE_THRESHOLD   = 80', config)
config = re.sub(r'CAUSALITY_WINDOW_SEC\s*=\s*6\.0', 'CAUSALITY_WINDOW_SEC  = 3.0', config)
config = re.sub(r'PASTE_CHAR_THRESHOLD\s*=\s*200', 'PASTE_CHAR_THRESHOLD  = 500', config)
config = re.sub(r'HEURISTIC_MIN_CHARS\s*=\s*80', 'HEURISTIC_MIN_CHARS   = 150', config)

doh_replacement = """# Known DoH/DoT provider IPs — only flag connections to these
DOH_PROVIDER_IPS = {
    # Cloudflare
    "1.1.1.1", "1.0.0.1", "2606:4700:4700::1111", "2606:4700:4700::1001",
    # Google
    "8.8.8.8", "8.8.4.4", "2001:4860:4860::8888", "2001:4860:4860::8844",
    # Quad9
    "9.9.9.9", "149.112.112.112",
    # AdGuard
    "94.140.14.14", "94.140.15.15",
    # Microsoft
    "13.107.4.52", "13.107.6.52", "204.79.197.203",
    # CleanBrowsing and Alternate DNS
    "185.228.168.9", "185.228.169.9",
    "76.76.2.0", "76.76.10.0",
}

SYSTEM_DNS_IPS = {
    "127.0.0.1", "::1", "127.0.0.53", "168.63.129.16"
}

INTERNAL_PORTS = {8001, 8002, 8003}
INTERNAL_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}
TRUTHLENS_ENV_KEY = 'TRUTHLENS_SERVICE'
INTERNAL_SERVICES = {'gigi', 'varchas', 'surakshan'}"""
config = re.sub(r'# Known DoH/DoT provider IPs.*?\}', doh_replacement, config, flags=re.DOTALL)

with open(f'{BASE_DIR}/config.py', 'w') as f:
    f.write(config)

# 2. capability.py
with open(f'{BASE_DIR}/capability.py', 'r') as f:
    cap = f.read()

nv_replacement = """    def _detect_nvidia(self) -> bool:
        \"\"\"Return True if pynvml initialises and at least one NVIDIA GPU is present.\"\"\"
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetCount()
            return count > 0
        except Exception as e:
            print(f"[CAPABILITY] NVIDIA GPU not detected: {e}")
            return False"""

is_internal_func = """
def _is_internal_service(proc) -> bool:
    try:
        from config import TRUTHLENS_ENV_KEY, INTERNAL_SERVICES
        envs = proc.environ()
        if envs and envs.get(TRUTHLENS_ENV_KEY):
            return True
        cmdline = " ".join(proc.cmdline() or []).lower()
        if any(svc in cmdline for svc in ['gigi/api', 'surakshan/api', 'varchas/api', 'gigi/main', 'surakshan/main', 'varchas/main']):
            return True
    except Exception:
        pass
    return False

"""
cap = cap.replace('caps = Capabilities()', is_internal_func + 'caps = Capabilities()')
with open(f'{BASE_DIR}/capability.py', 'w') as f:
    f.write(cap)

# 3. layers/network.py
with open(f'{BASE_DIR}/layers/network.py', 'r') as f:
    net = f.read()

net = net.replace('from config import VPN_PROCESS_NAMES, DOH_PORTS, AI_PORTS, DOH_PROVIDER_IPS', 'from config import VPN_PROCESS_NAMES, DOH_PORTS, AI_PORTS, DOH_PROVIDER_IPS, SYSTEM_DNS_IPS')

net_doh_base = """
    # Record which DoH provider IPs are already connected at startup
    _doh_baseline_ips.clear()
    if caps.can_read_connections:
        try:
            import psutil  # type: ignore
            for conn in psutil.net_connections(kind="inet"):
                try:
                    if conn.raddr:
                        _doh_baseline_ips.add(conn.raddr.ip)
                except Exception:
                    continue
        except Exception as e:
            print(f"[NETWORK] DoH baseline error: {e}")"""
net = re.sub(r'# Record which DoH provider IPs are already connected at startup.*?print\(f"\[NETWORK\] DoH baseline error: \{e\}"\)', net_doh_base.strip(), net, flags=re.DOTALL)

net_check_doh = """                if (remote_port in DOH_PORTS and
                        remote_ip in DOH_PROVIDER_IPS and
                        remote_ip not in _doh_baseline_ips and
                        remote_ip not in SYSTEM_DNS_IPS):"""
net = re.sub(r'if \(remote_port in DOH_PORTS and\s+remote_ip in DOH_PROVIDER_IPS and\s+remote_ip not in _doh_baseline_ips\):', net_check_doh, net)

# to_forensic_events for network
tfe_net = """def to_forensic_events(scan_result: Dict) -> List[Any]:
    from api import push_event
    class _FE:
        def __init__(self, **kw): self.__dict__.update(kw)
        def model_dump_json(self): import json; return json.dumps(self.__dict__)
    
    events = []
    sc = scan_result.get("score", 0)
    sev = 'critical' if sc>=8 else 'high' if sc>=6 else 'medium' if sc>=3 else 'low'
    for ev in scan_result.get("evidence", []):
        signal = 'network_anomaly'
        if 'VPN' in ev: signal = 'vpn_active'
        elif 'DoH' in ev: signal = 'doh_active'
        elif 'Long' in ev: signal = 'long_ai_conn'
        
        events.append(_FE(
            timestamp=time.time(), source='varchas', layer=scan_result.get('layer', 'network'),
            signal=signal, value=min(sc/10.0, 1.0), raw=scan_result.get("raw", {}),
            severity=sev, description=ev
        ))
    return events
"""
net = net.replace('# ─── Public API ───────────────────────────────────────────────────────────────', '# ─── Public API ───────────────────────────────────────────────────────────────\n\n' + tfe_net)

net = re.sub(r'(_conn_first_seen\[key\]\s*=\s*now\s*else:\s*held\s*=\s*now\s*-\s*_conn_first_seen\[key\]\s*if\s*held\s*>\s*5\.0:)([\s\S]*?raw\["long_ai_connections"\]\.append\(\{[\s\S]*?\}\))', r'\1\2\n                            try:\n                                ev_str = f"Long-held AI connection to {remote_ip} (open {held:.1f}s — inference pattern)"\n                                to_forensic_events({"layer":"network","score":10,"evidence":[ev_str],"raw":raw})[0] \n                                # Event pushed directly inside to_forensic_events using api.push_event if we change it\n                                from api import push_event, ForensicEvent\n                                push_event(ForensicEvent(timestamp=time.time(), source="varchas", layer="network", signal="long_ai_conn", value=1.0, raw=raw, severity="critical", description=ev_str))\n                            except Exception:\n                                pass', net)

with open(f'{BASE_DIR}/layers/network.py', 'w') as f:
    f.write(net)
