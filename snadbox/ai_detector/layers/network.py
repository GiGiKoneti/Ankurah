"""
layers/network.py — Detects AI evasion signals: VPN activation, DoH/DoT,
active connections, DNS monitoring, bandwidth spikes, TLS SNI inspection,
and long-held AI connections.

All scanners skip INTERNAL_HOSTS/PORTS and internal TruthLens services.
"""

import socket
import time
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from config import (
    VPN_PROCESS_NAMES, VPN_IFACE_PREFIXES, DOH_PORTS, AI_PORTS,
    DOH_PROVIDER_IPS, AI_DOMAINS, THREAT_DOMAINS, INTERNAL_PORTS,
    INTERNAL_HOSTS, SYSTEM_DNS_IPS, LONG_CONN_SEC,
)
from capability import caps, _is_internal_service

# ─── VPN baseline ─────────────────────────────────────────────────────────────
_vpn_baseline_procs:  Set[str] = set()
_vpn_baseline_ifaces: Set[str] = set()
_baseline_set  = False
_baseline_lock = threading.Lock()

# ─── DoH baseline ─────────────────────────────────────────────────────────────
_doh_baseline_ips: Set[str] = set()

# ─── Long-held connection tracking ───────────────────────────────────────────
# key = (laddr_ip, laddr_port, raddr_ip, raddr_port) → first_seen (monotonic)
_conn_first_seen: Dict[Tuple, float] = {}
_conn_lock        = threading.Lock()

# ─── Connection first-seen timestamps (for duration tracking) ─────────────────
_active_conn_seen: Dict[Tuple, float] = {}

# ─── Reverse DNS cache ────────────────────────────────────────────────────────
_rdns_cache: Dict[str, Tuple[Optional[str], float]] = {}
_rdns_lock   = threading.Lock()
_RDNS_TTL    = 60.0

# ─── Bandwidth baseline ───────────────────────────────────────────────────────
_bw_samples: List[float] = []      # bytes_sent history
_bw_lock     = threading.Lock()

# ─── Evasion flags (for aggregator) ──────────────────────────────────────────
_last_evasion_flags: List[str] = []
_evasion_lock = threading.Lock()


# ─── VPN baseline helpers ─────────────────────────────────────────────────────

def _collect_vpn_proc_names() -> Set[str]:
    """Return the set of VPN-related process names currently running."""
    names: Set[str] = set()
    try:
        import psutil  # type: ignore
        for proc in psutil.process_iter(["name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                for vpn in VPN_PROCESS_NAMES:
                    if vpn.lower() in pname:
                        names.add(pname)
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue
    except Exception as e:
        print(f"[NETWORK] _collect_vpn_proc_names error: {e}")
    return names


def _collect_vpn_ifaces() -> Set[str]:
    """Return set of VPN-style network interface names."""
    ifaces: Set[str] = set()
    try:
        import psutil  # type: ignore
        for iface_name in psutil.net_if_stats().keys():
            n = iface_name.lower()
            for prefix in VPN_IFACE_PREFIXES:
                if n.startswith(prefix):
                    ifaces.add(iface_name)
                    break
    except Exception as e:
        print(f"[NETWORK] _collect_vpn_ifaces error: {e}")
    return ifaces


def set_vpn_baseline() -> None:
    """Record VPN process, interface state, and DoH connections at session startup."""
    global _vpn_baseline_procs, _vpn_baseline_ifaces, _baseline_set
    try:
        with _baseline_lock:
            _vpn_baseline_procs  = _collect_vpn_proc_names()
            _vpn_baseline_ifaces = _collect_vpn_ifaces()
            _baseline_set        = True
        print(
            f"[NETWORK] VPN baseline set — procs: {_vpn_baseline_procs}, "
            f"ifaces: {_vpn_baseline_ifaces}"
        )
    except Exception as e:
        print(f"[NETWORK] set_vpn_baseline error: {e}")

    # Record ALL existing DoH connections at startup
    _doh_baseline_ips.clear()
    if caps.can_read_connections:
        try:
            import psutil  # type: ignore
            for conn in psutil.net_connections(kind="inet"):
                try:
                    if (conn.raddr
                            and conn.raddr.port in DOH_PORTS
                            and conn.raddr.ip in DOH_PROVIDER_IPS):
                        _doh_baseline_ips.add(conn.raddr.ip)
                except Exception:
                    continue
        except Exception as e:
            print(f"[NETWORK] DoH baseline error: {e}")

    print(f"[NETWORK] DoH baseline IPs recorded: {_doh_baseline_ips}")


# ─── Reverse DNS helper ───────────────────────────────────────────────────────

def _resolve_rdns(ip: str) -> Optional[str]:
    """Cached reverse-DNS lookup; caches None results too (prevents hammering)."""
    now = time.monotonic()
    with _rdns_lock:
        cached = _rdns_cache.get(ip)
        if cached is not None:
            hostname, ts = cached
            if now - ts < _RDNS_TTL:
                return hostname

    hostname: Optional[str] = None
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(1.0)
    try:
        result   = socket.gethostbyaddr(ip)
        hostname = result[0]
    except (socket.herror, socket.gaierror, socket.timeout, OSError):
        hostname = None
    except Exception as e:
        print(f"[NETWORK] rDNS error for {ip}: {e}")
        hostname = None
    finally:
        socket.setdefaulttimeout(old_timeout)

    with _rdns_lock:
        _rdns_cache[ip] = (hostname, now)
    return hostname


def _domain_matches(hostname: str, domain: str) -> bool:
    """Exact match: hostname == domain OR hostname.endswith('.' + domain)."""
    return hostname == domain or hostname.endswith("." + domain)


def _is_local_ip(ip: str) -> bool:
    """Return True if the IP is a private/local address (skip geolocation)."""
    try:
        import ipaddress
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except Exception:
        return ip.startswith("127.") or ip.startswith("192.168.") or ip == "::1"


# ─── Sub-scanner 2A — Active Connection Monitoring ───────────────────────────

def _scan_active_connections() -> Tuple[int, List[str], Dict]:
    """Monitor all active connections and capture metadata."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {"active_connections": []}

    if not caps.can_read_connections:
        return 0, [], raw

    try:
        import psutil  # type: ignore
        now = time.monotonic()

        try:
            conns = psutil.net_connections(kind="inet")
        except psutil.AccessDenied:
            return 0, [], raw
        except Exception as e:
            print(f"[NETWORK] active conn scan error: {e}")
            return 0, [], raw

        try:
            net_io = psutil.net_io_counters(pernic=False)
            bytes_sent = net_io.bytes_sent
            bytes_recv = net_io.bytes_recv
        except Exception:
            bytes_sent = bytes_recv = 0

        active_keys: Set[Tuple] = set()

        for conn in conns:
            try:
                if not conn.raddr:
                    continue
                remote_ip   = conn.raddr.ip
                remote_port = conn.raddr.port

                if remote_ip in INTERNAL_HOSTS or remote_ip.startswith("127."):
                    continue
                if remote_port in INTERNAL_PORTS:
                    continue

                # Self-exclusion
                try:
                    if conn.pid:
                        proc = psutil.Process(conn.pid)
                        if _is_internal_service(proc):
                            continue
                except Exception:
                    pass

                key = (
                    getattr(conn.laddr, "ip", ""),
                    getattr(conn.laddr, "port", 0),
                    remote_ip,
                    remote_port,
                )
                active_keys.add(key)

                proc_name = ""
                try:
                    if conn.pid:
                        proc_name = psutil.Process(conn.pid).name()
                except Exception:
                    pass

                # Connection duration
                with _active_conn_seen.setdefault(key, now) if False else _conn_lock:
                    if key not in _active_conn_seen:
                        _active_conn_seen[key] = now
                    held_sec = now - _active_conn_seen.get(key, now)

                entry = {
                    "remote_ip":    remote_ip,
                    "remote_port":  remote_port,
                    "proc_name":    proc_name,
                    "status":       conn.status,
                    "held_sec":     round(held_sec, 1) if key in _active_conn_seen else 0.0,
                    "is_local":     _is_local_ip(remote_ip),
                }
                raw["active_connections"].append(entry)

            except Exception as e:
                print(f"[NETWORK] active conn inner error: {e}")
                continue

        raw["total_bytes_sent"] = bytes_sent
        raw["total_bytes_recv"] = bytes_recv

    except Exception as e:
        print(f"[NETWORK] _scan_active_connections error: {e}")
        raw["conn_error"] = str(e)

    return score, evidence, raw


# ─── Sub-scanner 2B — DNS Monitoring ─────────────────────────────────────────

def _scan_dns_connections() -> Tuple[int, List[str], Dict]:
    """Reverse-DNS lookup on remote IPs; exact-match against AI_DOMAINS."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {"dns_hits": []}

    if not caps.can_read_connections:
        return 0, [], raw

    try:
        import psutil  # type: ignore

        try:
            conns = psutil.net_connections(kind="inet")
        except psutil.AccessDenied:
            return 0, [], raw

        matched: Set[str] = set()

        for conn in conns:
            try:
                if not conn.raddr:
                    continue
                remote_ip = conn.raddr.ip

                if remote_ip in INTERNAL_HOSTS:
                    continue
                if _is_local_ip(remote_ip):
                    continue

                try:
                    if conn.pid:
                        proc = psutil.Process(conn.pid)
                        if _is_internal_service(proc):
                            continue
                except Exception:
                    pass

                hostname = _resolve_rdns(remote_ip)
                if not hostname:
                    continue

                # Check AI domains — exact match only
                all_domains = list(AI_DOMAINS) + list(THREAT_DOMAINS.keys())
                for domain in all_domains:
                    if domain not in matched and _domain_matches(hostname, domain):
                        matched.add(domain)
                        severity_hint = THREAT_DOMAINS.get(domain, "high")
                        score = min(score + 4, 10)
                        ev_str = (
                            f"DNS match: connection to {hostname} "
                            f"({domain}) IP {remote_ip}"
                        )
                        evidence.append(ev_str)
                        raw["dns_hits"].append({
                            "hostname":  hostname,
                            "domain":    domain,
                            "remote_ip": remote_ip,
                            "severity":  severity_hint,
                        })
                        break

            except Exception as e:
                print(f"[NETWORK] DNS scan inner error: {e}")
                continue

    except Exception as e:
        print(f"[NETWORK] _scan_dns_connections error: {e}")
        raw["dns_error"] = str(e)

    return score, evidence, raw


# ─── Sub-scanner 2C — Bandwidth Spike Detection ───────────────────────────────

def _scan_bandwidth() -> Tuple[int, List[str], Dict]:
    """Detect upload spikes (sudden > 2x baseline) indicating answer exfiltration."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {}

    try:
        import psutil  # type: ignore
        net_io = psutil.net_io_counters()
        bytes_sent = net_io.bytes_sent

        mbps_upload = 0.0
        spike_detected = False

        with _bw_lock:
            _bw_samples.append(bytes_sent)
            if len(_bw_samples) > 30:
                _bw_samples.pop(0)

            if len(_bw_samples) >= 3:
                recent  = _bw_samples[-1]
                prev    = _bw_samples[-2]
                delta   = recent - prev
                mbps_upload = delta * 8 / 1_000_000

                # Baseline = median of older samples
                baseline_samples = sorted(_bw_samples[:-2])
                if baseline_samples:
                    median_bw = baseline_samples[len(baseline_samples) // 2]
                    prev_baseline = _bw_samples[-3] if len(_bw_samples) >= 3 else median_bw
                    baseline_delta = max(_bw_samples[-2] - prev_baseline, 1)
                    if delta > baseline_delta * 2 and delta > 100_000:  # > 100KB burst
                        spike_detected = True
                        score = min(score + 3, 10)
                        evidence.append(
                            f"Upload spike detected: {mbps_upload:.2f} Mbps "
                            f"(>2x baseline — possible answer exfiltration)"
                        )

        raw["upload_mbps"]     = round(mbps_upload, 3)
        raw["spike_detected"]  = spike_detected
        raw["bw_samples_count"] = len(_bw_samples)

    except Exception as e:
        print(f"[NETWORK] _scan_bandwidth error: {e}")
        raw["bw_error"] = str(e)

    return score, evidence, raw


# ─── Sub-scanner 2D — TLS SNI Inspection ─────────────────────────────────────

def _scan_tls_sni() -> Tuple[int, List[str], Dict]:
    """Read TLS SNI destination from active connections (Linux /proc, Windows socket).

    Does NOT decrypt traffic; only reads the plaintext SNI field.
    """
    score    = 0
    evidence: List[str] = []
    raw: Dict = {"sni_hits": []}

    if caps.os_name == "Linux":
        return _scan_tls_sni_linux(score, evidence, raw)
    elif caps.os_name == "Windows":
        return _scan_tls_sni_windows(score, evidence, raw)
    return score, evidence, raw


def _scan_tls_sni_linux(score, evidence, raw) -> Tuple[int, List[str], Dict]:
    """Linux TLS SNI: cross-reference /proc/net/tcp with /proc/PID/fd socket inodes."""
    try:
        import psutil  # type: ignore

        # Build inode → remote_ip:port map from /proc/net/tcp and /proc/net/tcp6
        inode_map: Dict[str, str] = {}
        for tcp_file in ["/proc/net/tcp", "/proc/net/tcp6"]:
            if not __import__("os").path.isfile(tcp_file):
                continue
            try:
                with open(tcp_file) as f:
                    for line in f.readlines()[1:]:
                        parts = line.split()
                        if len(parts) < 10:
                            continue
                        inode = parts[9]
                        # Decode hex remote address
                        try:
                            remote_hex = parts[2]
                            port_hex   = remote_hex.split(":")[1]
                            ip_hex     = remote_hex.split(":")[0]
                            port       = int(port_hex, 16)
                            # IPv4: reverse 4-byte little-endian
                            if len(ip_hex) == 8:
                                ip_bytes = bytes.fromhex(ip_hex)
                                remote_ip = ".".join(str(b) for b in reversed(ip_bytes))
                            else:
                                remote_ip = ip_hex  # IPv6 — simplified
                            inode_map[inode] = f"{remote_ip}:{port}"
                        except Exception:
                            pass
            except Exception as e:
                print(f"[NETWORK] read {tcp_file} error: {e}")

        # Match inodes to processes and check ports 443 (HTTPS)
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if _is_internal_service(proc):
                    continue
                fd_dir = f"/proc/{proc.pid}/fd"
                if not __import__("os").path.isdir(fd_dir):
                    continue
                for fd in __import__("os").listdir(fd_dir):
                    try:
                        target = __import__("os").readlink(
                            __import__("os").path.join(fd_dir, fd)
                        )
                        if target.startswith("socket:["):
                            inode = target[8:-1]
                            addr  = inode_map.get(inode, "")
                            if addr:
                                parts = addr.rsplit(":", 1)
                                if len(parts) == 2:
                                    remote_ip = parts[0]
                                    port      = int(parts[1])
                                    if port == 443 and not _is_local_ip(remote_ip):
                                        hostname = _resolve_rdns(remote_ip)
                                        if hostname:
                                            for domain in list(AI_DOMAINS) + list(THREAT_DOMAINS.keys()):
                                                if _domain_matches(hostname, domain):
                                                    score = min(score + 3, 10)
                                                    ev_str = (
                                                        f"TLS SNI: HTTPS to {hostname} "
                                                        f"({domain}) from '{proc.info.get('name')}'"
                                                    )
                                                    evidence.append(ev_str)
                                                    raw["sni_hits"].append({
                                                        "hostname":  hostname,
                                                        "domain":    domain,
                                                        "remote_ip": remote_ip,
                                                        "proc":      proc.info.get("name"),
                                                    })
                                                    break
                    except Exception:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception:
                continue

    except Exception as e:
        print(f"[NETWORK] _scan_tls_sni_linux error: {e}")
        raw["sni_error"] = str(e)

    return score, evidence, raw


def _scan_tls_sni_windows(score, evidence, raw) -> Tuple[int, List[str], Dict]:
    """Windows TLS SNI: use WMI/psutil connection table and rDNS lookup."""
    try:
        import psutil  # type: ignore
        for conn in psutil.net_connections(kind="inet"):
            try:
                if not conn.raddr:
                    continue
                remote_ip   = conn.raddr.ip
                remote_port = conn.raddr.port

                if remote_port != 443:
                    continue
                if _is_local_ip(remote_ip):
                    continue

                try:
                    if conn.pid:
                        proc = psutil.Process(conn.pid)
                        if _is_internal_service(proc):
                            continue
                except Exception:
                    pass

                hostname = _resolve_rdns(remote_ip)
                if hostname:
                    for domain in list(AI_DOMAINS) + list(THREAT_DOMAINS.keys()):
                        if _domain_matches(hostname, domain):
                            score = min(score + 3, 10)
                            evidence.append(
                                f"TLS SNI: HTTPS to {hostname} ({domain}) IP {remote_ip}"
                            )
                            raw["sni_hits"].append({
                                "hostname":  hostname,
                                "domain":    domain,
                                "remote_ip": remote_ip,
                            })
                            break
            except Exception:
                continue
    except Exception as e:
        print(f"[NETWORK] _scan_tls_sni_windows error: {e}")
        raw["sni_error"] = str(e)

    return score, evidence, raw


# ─── Sub-scanner 2E — VPN/Evasion Detection ──────────────────────────────────

def _check_vpn() -> Tuple[int, List[str], Dict]:
    """Detect VPN activation after session start."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {}

    try:
        current_procs  = _collect_vpn_proc_names()
        current_ifaces = _collect_vpn_ifaces()

        with _baseline_lock:
            new_procs  = current_procs  - _vpn_baseline_procs
            new_ifaces = current_ifaces - _vpn_baseline_ifaces

        raw["vpn_procs_now"]   = sorted(current_procs)
        raw["vpn_ifaces_now"]  = sorted(current_ifaces)
        raw["vpn_new_procs"]   = sorted(new_procs)
        raw["vpn_new_ifaces"]  = sorted(new_ifaces)

        for p in new_procs:
            score = min(score + 5, 10)
            evidence.append(f"VPN process started mid-session: {p}")

        for iface in new_ifaces:
            score = min(score + 5, 10)
            evidence.append(f"VPN interface appeared mid-session: {iface}")

    except Exception as e:
        print(f"[NETWORK] VPN check error: {e}")
        raw["vpn_error"] = str(e)

    return score, evidence, raw


# ─── Sub-scanner 2F — DoH Detection ──────────────────────────────────────────

def _check_doh() -> Tuple[int, List[str], Dict]:
    """Detect new DoH/DoT connections (CRITICAL: only flag if not in baseline).

    All four conditions must be true:
      a) port in DOH_PORTS (853 or 5053)
      b) remote_ip in DOH_PROVIDER_IPS
      c) remote_ip NOT in _doh_baseline_ips
      d) remote_ip NOT in SYSTEM_DNS_IPS
    """
    score    = 0
    evidence: List[str] = []
    raw: Dict = {"doh_connections": []}

    if not caps.can_read_connections:
        return 0, [], raw

    try:
        import psutil  # type: ignore
        conns = psutil.net_connections(kind="inet")
        for conn in conns:
            try:
                if not conn.raddr:
                    continue
                remote_ip   = conn.raddr.ip
                remote_port = conn.raddr.port

                # All four conditions must be met
                if (remote_port in DOH_PORTS
                        and remote_ip in DOH_PROVIDER_IPS
                        and remote_ip not in _doh_baseline_ips
                        and remote_ip not in SYSTEM_DNS_IPS):
                    entry = {
                        "remote_ip":   remote_ip,
                        "remote_port": remote_port,
                        "status":      conn.status,
                    }
                    raw["doh_connections"].append(entry)
                    score = min(score + 3, 10)
                    evidence.append(
                        f"New encrypted DNS (DoH/DoT) connection to "
                        f"{remote_ip}:{remote_port} (started mid-session)"
                    )

            except Exception:
                continue
    except psutil.AccessDenied:
        print("[NETWORK] AccessDenied on net_connections (DoH check)")
    except Exception as e:
        print(f"[NETWORK] DoH check error: {e}")
        raw["doh_error"] = str(e)

    return score, evidence, raw


# ─── Sub-scanner 2G — Long AI Connection Timing ──────────────────────────────

def _check_long_ai_connections() -> Tuple[int, List[str], Dict]:
    """Flag connections to AI IP ranges held open > LONG_CONN_SEC. Push ForensicEvent immediately."""
    score    = 0
    evidence: List[str] = []
    raw: Dict = {"long_ai_connections": []}

    if not caps.can_read_connections:
        return 0, [], raw

    try:
        import psutil  # type: ignore
        from db.ai_domains import get_all_ai_ips

        ai_ips = get_all_ai_ips()
        now    = time.monotonic()

        try:
            conns = psutil.net_connections(kind="inet")
        except psutil.AccessDenied:
            return 0, [], raw

        active_keys: Set[Tuple] = set()

        for conn in conns:
            try:
                if not conn.raddr:
                    continue
                remote_ip = conn.raddr.ip
                if remote_ip not in ai_ips:
                    continue
                if remote_ip in INTERNAL_HOSTS:
                    continue

                try:
                    if conn.pid:
                        proc = psutil.Process(conn.pid)
                        if _is_internal_service(proc):
                            continue
                except Exception:
                    pass

                key = (
                    getattr(conn.laddr, "ip", ""),
                    getattr(conn.laddr, "port", 0),
                    remote_ip,
                    conn.raddr.port,
                )
                active_keys.add(key)

                with _conn_lock:
                    if key not in _conn_first_seen:
                        _conn_first_seen[key] = now
                    else:
                        held = now - _conn_first_seen[key]
                        if held > LONG_CONN_SEC:
                            score = min(score + 4, 10)
                            ev_str = (
                                f"Long-held AI connection to {remote_ip} "
                                f"(open {held:.1f}s — inference pattern)"
                            )
                            evidence.append(ev_str)
                            raw["long_ai_connections"].append({
                                "remote_ip": remote_ip,
                                "held_sec":  round(held, 1),
                            })
                            _push_long_conn_event(remote_ip, held, score)

            except Exception:
                continue

        # Prune stale connection records
        try:
            with _conn_lock:
                stale = [k for k in list(_conn_first_seen.keys()) if k not in active_keys]
                for k in stale:
                    del _conn_first_seen[k]
        except Exception as e:
            print(f"[NETWORK] connection prune error: {e}")

    except Exception as e:
        print(f"[NETWORK] long connection check error: {e}")
        raw["long_conn_error"] = str(e)

    return score, evidence, raw


def _push_long_conn_event(remote_ip: str, held_sec: float, score: int) -> None:
    """Push a long-AI-connection ForensicEvent immediately."""
    try:
        from api import push_event
        from shared.schemas import ForensicEvent
        push_event(ForensicEvent(
            timestamp=time.time(),
            source="varchas",
            layer="network",
            signal="ai_domain",
            value=min(score / 10.0, 1.0),
            raw={"remote_ip": remote_ip, "held_sec": held_sec},
            severity="high",
            description=(
                f"Long-held AI connection to {remote_ip} "
                f"(open {held_sec:.1f}s — inference pattern)"
            ),
        ))
    except Exception:
        pass


# ─── ForensicEvent converter ──────────────────────────────────────────────────

def to_forensic_events(scan_result: dict) -> list:
    """Convert a network layer result dict into a list of ForensicEvent objects."""
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
                "vpn_evasion"   if "VPN" in ev_str else
                "doh_evasion"   if "DoH" in ev_str or "encrypted DNS" in ev_str else
                "ai_domain"     if "AI" in ev_str or "domain" in ev_str.lower() else
                "network"
            )
            event = ForensicEvent(
                timestamp=time.time(),
                source="varchas",
                layer=scan_result.get("layer", "network"),
                signal=signal,
                value=value,
                raw=scan_result.get("raw", {}),
                severity=severity,
                description=ev_str,
            )
            events.append(event)
    except Exception as e:
        print(f"[NETWORK] to_forensic_events error: {e}")
    return events


# ─── Public API ───────────────────────────────────────────────────────────────

def run_network_scan() -> dict:
    """Run all network sub-scanners; return unified layer result dict."""
    all_evidence: List[str] = []
    evasion_flags: List[str] = []
    raw: Dict[str, Any]      = {}
    total_score = 0

    try:
        s, ev, r = _check_vpn()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
        if s > 0:
            evasion_flags.extend(ev)
    except Exception as e:
        print(f"[NETWORK] VPN check error: {e}")

    try:
        s, ev, r = _check_doh()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
        if s > 0:
            evasion_flags.extend(ev)
    except Exception as e:
        print(f"[NETWORK] DoH check error: {e}")

    try:
        s, ev, r = _check_long_ai_connections()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
    except Exception as e:
        print(f"[NETWORK] long connection check error: {e}")

    try:
        s, ev, r = _scan_dns_connections()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
    except Exception as e:
        print(f"[NETWORK] DNS scan error: {e}")

    try:
        s, ev, r = _scan_bandwidth()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
    except Exception as e:
        print(f"[NETWORK] bandwidth scan error: {e}")

    try:
        s, ev, r = _scan_tls_sni()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
    except Exception as e:
        print(f"[NETWORK] TLS SNI scan error: {e}")

    try:
        s, ev, r = _scan_active_connections()
        # Active connections contribute to raw data but not directly to score
        raw.update(r)
    except Exception as e:
        print(f"[NETWORK] active connection scan error: {e}")

    with _evasion_lock:
        _last_evasion_flags.clear()
        _last_evasion_flags.extend(evasion_flags)

    raw["evasion_flags"] = evasion_flags

    confidence = 1.0 if caps.can_read_connections else 0.3

    return {
        "layer":      "network",
        "score":      min(total_score, 10),
        "evidence":   all_evidence,
        "confidence": round(confidence, 2),
        "raw":        raw,
    }


def get_evasion_flags() -> List[str]:
    """Return the evasion flags recorded in the most recent network scan."""
    try:
        with _evasion_lock:
            return list(_last_evasion_flags)
    except Exception as e:
        print(f"[NETWORK] get_evasion_flags error: {e}")
        return []
