"""
layers/network.py — Detects AI evasion signals: VPN activation, DoH/DoT
encrypted DNS switching, and long-held connections to AI API servers.

This layer focuses on evasion and traffic-pattern signals, complementing
browser.py which focuses on AI domain identification.
"""

import time
import threading
from typing import List, Dict, Any, Set, Tuple

from config import VPN_PROCESS_NAMES, DOH_PORTS, AI_PORTS, DOH_PROVIDER_IPS
from capability import caps

# ─── VPN baseline (recorded at startup) ──────────────────────────────────────
_vpn_baseline_procs: Set[str] = set()        # process names present at startup
_vpn_baseline_ifaces: Set[str] = set()       # interface names present at startup
_baseline_set     = False
_baseline_lock    = threading.Lock()

# ─── DoH baseline (recorded at startup) ──────────────────────────────────────
_doh_baseline_ips: Set[str] = set()          # DoH provider IPs connected at startup

# ─── Long-held connection tracking ───────────────────────────────────────────
# key = (laddr_ip, laddr_port, raddr_ip, raddr_port) → first_seen timestamp
_conn_first_seen: Dict[Tuple, float] = {}
_conn_lock        = threading.Lock()


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
    """Return set of VPN-style network interface names (tun*, wg*, ppp*, TAP*)."""
    ifaces: Set[str] = set()
    try:
        import psutil  # type: ignore
        for iface_name in psutil.net_if_stats().keys():
            n = iface_name.lower()
            if n.startswith(("tun", "wg", "ppp", "tap", "utun")):
                ifaces.add(iface_name)
    except Exception as e:
        print(f"[NETWORK] _collect_vpn_ifaces error: {e}")
    return ifaces


def set_vpn_baseline() -> None:
    """Record the VPN process and interface state at session startup."""
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

    # Record which DoH provider IPs are already connected at startup
    _doh_baseline_ips.clear()
    if caps.can_read_connections:
        try:
            import psutil  # type: ignore
            for conn in psutil.net_connections(kind="inet"):
                try:
                    if (conn.raddr and
                            conn.raddr.port in DOH_PORTS and
                            conn.raddr.ip in DOH_PROVIDER_IPS):
                        _doh_baseline_ips.add(conn.raddr.ip)
                except Exception:
                    continue
        except Exception as e:
            print(f"[NETWORK] DoH baseline error: {e}")


# ─── Sub-checks ───────────────────────────────────────────────────────────────

def _check_vpn() -> Tuple[int, List[str], Dict]:
    """Detect VPN activation after session start; returns (score, evidence, raw)."""
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

        if new_procs:
            score = min(score + 5, 10)
            evidence.append(
                f"VPN process(es) started mid-session: {', '.join(new_procs)}"
            )
        if new_ifaces:
            score = min(score + 5, 10)
            evidence.append(
                f"VPN interface(s) appeared mid-session: {', '.join(new_ifaces)}"
            )
    except Exception as e:
        print(f"[NETWORK] VPN check error: {e}")
        raw["vpn_error"] = str(e)

    return score, evidence, raw


def _check_doh() -> Tuple[int, List[str], Dict]:
    """Detect DoH/DoT connections (encrypted DNS) as evasion signals."""
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
                # Only flag if: correct port AND known DoH provider
                # AND this IP was not already connected at baseline
                if (remote_port in DOH_PORTS and
                        remote_ip in DOH_PROVIDER_IPS and
                        remote_ip not in _doh_baseline_ips):
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


def _check_long_ai_connections() -> Tuple[int, List[str], Dict]:
    """Flag connections to AI IP ranges held open > 5 seconds (inference pattern)."""
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
            print("[NETWORK] AccessDenied on net_connections (long connection check)")
            return 0, [], raw

        active_keys: Set[Tuple] = set()

        for conn in conns:
            try:
                if not conn.raddr:
                    continue
                remote_ip = conn.raddr.ip
                if remote_ip not in ai_ips:
                    continue

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
                        if held > 5.0:
                            score = min(score + 4, 10)
                            evidence.append(
                                f"Long-held AI connection to {remote_ip} "
                                f"(open {held:.1f}s — inference pattern)"
                            )
                            raw["long_ai_connections"].append({
                                "remote_ip": remote_ip,
                                "held_sec":  round(held, 1),
                            })

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


# ─── Public API ───────────────────────────────────────────────────────────────

# Record evasion flags so the aggregator can apply the evasion penalty
_last_evasion_flags: List[str] = []
_evasion_lock = threading.Lock()


def run_network_scan() -> dict:
    """Run VPN, DoH, and long-connection checks; return unified layer result dict."""
    all_evidence: List[str] = []
    evasion_flags: List[str] = []
    raw: Dict[str, Any]      = {}
    total_score = 0

    # ── VPN ─────────────────────────────────────────────────────────────
    try:
        s, ev, r = _check_vpn()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
        if s > 0:
            evasion_flags.extend(ev)
    except Exception as e:
        print(f"[NETWORK] VPN check top-level error: {e}")

    # ── DoH / DoT ────────────────────────────────────────────────────────
    try:
        s, ev, r = _check_doh()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
        if s > 0:
            evasion_flags.extend(ev)
    except Exception as e:
        print(f"[NETWORK] DoH check top-level error: {e}")

    # ── Long AI connections ───────────────────────────────────────────────
    try:
        s, ev, r = _check_long_ai_connections()
        total_score = min(total_score + s, 10)
        all_evidence.extend(ev)
        raw.update(r)
    except Exception as e:
        print(f"[NETWORK] long connection check top-level error: {e}")

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
