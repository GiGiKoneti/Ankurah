"""
main.py — Varchas entry point.

MUST be the very first thing: set TRUTHLENS_SERVICE env var before any imports
so that capability.py and all layers see it when _is_internal_service() runs.

Startup sequence:
  1. Set TRUTHLENS_SERVICE='varchas'
  2. Prompt for consent
  3. Detect capabilities (caps)
  4. Build AI domain IP cache
  5. Set peripheral baseline
  6. Start background daemons: clipboard monitor, keyboard listener,
     model file watcher, 10Hz hardware sampler, FastAPI server
  7. Set VPN/DoH baseline
  8. Main detection loop (every POLL_INTERVAL_NORMAL seconds)
"""

# ── CRITICAL: Must be first executable statement ───────────────────────────
import os
os.environ["TRUTHLENS_SERVICE"] = "varchas"
# ──────────────────────────────────────────────────────────────────────────

import time
import threading

from config import (
    POLL_INTERVAL_NORMAL, EMIT_INTERVAL, API_PORT, API_HOST,
)


# ─── Consent prompt ────────────────────────────────────────────────────────────

def _prompt_consent() -> bool:
    """Ask the user for explicit monitoring consent. Return True to proceed."""
    print("\n" + "═" * 60)
    print(" Varchas — Systems Intelligence Layer")
    print(" TruthLens AI Interview Integrity System")
    print("═" * 60)
    print()
    print("This service monitors your system for signs of AI-assisted")
    print("cheating during an interview session. Monitoring includes:")
    print()
    print("  • Running processes and loaded libraries")
    print("  • Network connections and DNS queries")
    print("  • GPU/CPU/RAM/Disk usage patterns")
    print("  • Clipboard content (size and style — not stored)")
    print("  • Keyboard timing metadata (not key values)")
    print("  • USB and Bluetooth devices")
    print("  • Browser window titles")
    print()
    print("No personal data is transmitted. Output is kept locally.")
    print()
    try:
        response = input("Do you consent to monitoring? [yes/no]: ").strip().lower()
        return response in ("yes", "y")
    except KeyboardInterrupt:
        return False
    except EOFError:
        # Non-interactive mode — proceed
        return True


# ─── Detection loop ────────────────────────────────────────────────────────────

def _detection_loop() -> None:
    """Run all layer scans on POLL_INTERVAL_NORMAL; add to aggregator window."""
    from layers.process import run_process_scan
    from layers.network import run_network_scan
    from layers.hardware import run_hardware_scan
    from layers.behavioral import run_behavioral_scan
    from layers.browser import run_browser_scan
    from layers.stealth_windows import run_stealth_window_scan
    from layers.peripheral import run_peripheral_scan
    from aggregator import add_snapshot, compute_score
    from api import emit

    last_emit_time = 0.0

    while True:
        try:
            # Run all layer scans
            proc_res   = run_process_scan()
            net_res    = run_network_scan()
            hw_res     = run_hardware_scan()
            behav_res  = run_behavioral_scan()
            browser_res = run_browser_scan()
            stealth_res = run_stealth_window_scan()
            periph_res  = run_peripheral_scan()

            snapshot = [
                proc_res, net_res, hw_res,
                behav_res, browser_res, stealth_res, periph_res,
            ]
            add_snapshot(snapshot)

            # Periodic score emit
            now = time.time()
            if now - last_emit_time >= EMIT_INTERVAL:
                payload   = compute_score()
                emit(payload)
                last_emit_time = now
                score = payload.get("hardware_ai_score", 0.0)
                flag_count = len(payload.get("evasion_flags", []))
                evid_count = len(payload.get("evidence", []))
                print(
                    f"[VARCHAS] Score={score:.1f}/100 | "
                    f"Evasion flags={flag_count} | "
                    f"Evidence items={evid_count} | "
                    f"Confidence={payload.get('confidence', 0):.2f}"
                )

        except Exception as e:
            print(f"[MAIN] detection loop error: {e}")

        time.sleep(POLL_INTERVAL_NORMAL)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    """Full startup sequence, then run the detection loop."""
    # ── 1. Consent ─────────────────────────────────────────────────────────
    if not _prompt_consent():
        print("[VARCHAS] Monitoring denied. Exiting.")
        return

    # ── 2. Capabilities ────────────────────────────────────────────────────
    from capability import caps  # triggers capability detection and prints report

    # ── 3. Build AI domain IP cache ────────────────────────────────────────
    try:
        from db.ai_domains import build_domain_cache
        t_cache = threading.Thread(target=build_domain_cache, name="domain-cache", daemon=True)
        t_cache.start()
        print("[STARTUP] Building AI domain IP cache...")
    except Exception as e:
        print(f"[MAIN] domain cache error: {e}")

    # ── 4. Peripheral baseline ────────────────────────────────────────────
    try:
        from layers.peripheral import set_peripheral_baseline
        set_peripheral_baseline()
    except Exception as e:
        print(f"[MAIN] peripheral baseline error: {e}")

    # ── 5. Background daemon threads ──────────────────────────────────────

    # Clipboard monitor
    try:
        from layers.behavioral import start_clipboard_monitor
        start_clipboard_monitor()
    except Exception as e:
        print(f"[MAIN] clipboard monitor error: {e}")

    # Keyboard listener (timing metadata only)
    try:
        from layers.behavioral import start_keyboard_listener
        start_keyboard_listener()
    except Exception as e:
        print(f"[MAIN] keyboard listener error: {e}")

    # Model file watcher
    try:
        from layers.process import start_model_file_watcher
        start_model_file_watcher()
    except Exception as e:
        print(f"[MAIN] model file watcher error: {e}")

    # 10Hz hardware sampler
    try:
        from layers.hardware import start_hw_sampler
        start_hw_sampler()
    except Exception as e:
        print(f"[MAIN] hardware sampler error: {e}")

    # FastAPI server (from api.py — NOT emitter.py)
    try:
        from api import start_api_server
        start_api_server()
    except Exception as e:
        print(f"[MAIN] API server startup error: {e}")

    # ── 6. VPN / DoH baseline ─────────────────────────────────────────────
    try:
        from layers.network import set_vpn_baseline
        set_vpn_baseline()
    except Exception as e:
        print(f"[MAIN] VPN baseline error: {e}")

    print()
    print("╔══════════════════════════════════════════╗")
    print("║  VARCHAS MONITORING ACTIVE               ║")
    print(f"║  API:  http://{API_HOST}:{API_PORT}         ║")
    print("║  Stream: ws://0.0.0.0:8002/stream/system ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # ── 7. Detection loop ─────────────────────────────────────────────────
    _detection_loop()


if __name__ == "__main__":
    main()
