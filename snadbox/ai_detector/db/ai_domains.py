"""
db/ai_domains.py — Resolves known AI API domains to IP addresses at startup.

The IP cache is used by network.py and browser.py to match live connections
without performing DNS lookups in the hot detection loop. DNS failures are
silently skipped so the cache is always a best-effort partial map.
"""

import socket
import threading
import time
from typing import Dict, Set

from config import AI_DOMAINS

# ─── Module-level state ──────────────────────────────────────────────────────
# Maps IP string → domain name (many-to-one: a domain may have multiple IPs)
_ip_to_domain: Dict[str, str] = {}
_ip_cache_lock = threading.Lock()

# Track the last time the cache was refreshed
_last_refresh: float = 0.0
_CACHE_TTL: float = 300.0   # rebuild the IP cache every 5 minutes


def build_ip_cache() -> None:
    """Resolve all known AI domains to IPs and populate the in-memory cache."""
    global _last_refresh
    resolved: Dict[str, str] = {}
    for domain in AI_DOMAINS:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(2)
        try:
            # getaddrinfo returns multiple results (IPv4 + IPv6 + aliases)
            infos = socket.getaddrinfo(domain, None)
            for info in infos:
                ip = info[4][0]
                resolved[ip] = domain
        except socket.timeout:
            # DNS timeout — skip silently
            pass
        except OSError:
            # No network, NXDOMAIN, etc. — skip silently
            pass
        except Exception as e:
            print(f"[DB] DNS resolution error for {domain}: {e}")
        finally:
            socket.setdefaulttimeout(old_timeout)

    with _ip_cache_lock:
        _ip_to_domain.clear()
        _ip_to_domain.update(resolved)
        _last_refresh = time.monotonic()

    print(f"[DB] IP cache built: {len(resolved)} IPs resolved from {len(AI_DOMAINS)} domains")


def get_domain_for_ip(ip: str) -> str | None:
    """Return the AI domain name for a given IP, or None if not in cache."""
    try:
        with _ip_cache_lock:
            _maybe_refresh()
            return _ip_to_domain.get(ip)
    except Exception as e:
        print(f"[DB] get_domain_for_ip error: {e}")
        return None


def get_all_ai_ips() -> Set[str]:
    """Return the current set of known AI IP addresses."""
    try:
        with _ip_cache_lock:
            _maybe_refresh()
            return set(_ip_to_domain.keys())
    except Exception as e:
        print(f"[DB] get_all_ai_ips error: {e}")
        return set()


def _maybe_refresh() -> None:
    """Silently trigger a background cache refresh if the TTL has expired (called under lock)."""
    global _last_refresh
    if time.monotonic() - _last_refresh > _CACHE_TTL:
        # Kick off a background refresh so we don't block callers
        t = threading.Thread(target=build_ip_cache, daemon=True, name="ip-cache-refresh")
        t.start()
        # Update _last_refresh optimistically to avoid spawning many threads
        _last_refresh = time.monotonic()
