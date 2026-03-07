"""
main.py — Entry point for the AI Detection System (hardware/network layer).

Startup sequence:
  1. Consent prompt — exit if not YES
  2. Instantiate caps (capability.py runs Capabilities() on import)
  3. Call build_ip_cache() from db/ai_domains.py
  4. Start clipboard monitor background thread (behavioral.py)
  5. Start model file watcher background thread (process.py)
  6. Start WebSocket server background thread (emitter.py)
  7. Set VPN baseline (network.py)
  8. Print ready message
  9. Enter detection_loop()

Expected score ranges (see comments below for scenario analysis):
  - Baseline (nothing AI running):         0–15
  - ChatGPT open in browser:              45–70
  - Ollama running locally:               55–80
  - Both simultaneously:                 75–100
"""

import sys
import time
import traceback

# ─── Consent prompt ───────────────────────────────────────────────────────────
# Must happen BEFORE any other imports that start background threads.

_CONSENT_TEXT = """
╔══════════════════════════════════════════════════════════════════╗
║               AI DETECTION SYSTEM — CONSENT NOTICE              ║
╠══════════════════════════════════════════════════════════════════╣
║  This tool monitors the following on this machine:               ║
║  • Active window titles                                          ║
║  • Running processes and loaded libraries                        ║
║  • Network connections (IP only, no packet content)              ║
║  • GPU / CPU / RAM utilisation statistics                        ║
║  • Clipboard paste events (size and style only — NOT content)    ║
║  • File open events for AI model file types                      ║
║                                                                  ║
║  All data stays LOCAL. Nothing is transmitted externally.        ║
║  A JSON score is output every 30 s to API port 8002 and to       ║
║  ai_detection_output.json.                                       ║
╚══════════════════════════════════════════════════════════════════╝
"""


def _show_consent() -> None:
    """Display the consent notice and exit if the user does not type YES."""
    print(_CONSENT_TEXT)
    try:
        response = input("Type YES to proceed: ").strip()
    except (EOFError, KeyboardInterrupt):
        response = ""
    if response != "YES":
        print("Consent not given — exiting.")
        sys.exit(0)


# ─── Main startup ─────────────────────────────────────────────────────────────

def _startup() -> None:
    """Import everything and start background threads in the correct order."""
    # Step 2 — capability singleton (imports trigger Capabilities() + report)
    from capability import caps

    # Step 3 — DNS IP cache (background-friendly; skip on error)
    try:
        from db.ai_domains import build_ip_cache
        build_ip_cache()
    except Exception as e:
        print(f"[MAIN] IP cache build error (non-fatal): {e}")

    # Step 4 — Clipboard monitor
    try:
        from layers.behavioral import start_clipboard_monitor
        start_clipboard_monitor()
    except Exception as e:
        print(f"[MAIN] Clipboard monitor start error (non-fatal): {e}")

    # Step 5 — Model file watcher
    try:
        from layers.process import start_model_file_watcher
        start_model_file_watcher()
    except Exception as e:
        print(f"[MAIN] Model file watcher start error (non-fatal): {e}")

    # Step 6 — FastAPI service & Hardware 10Hz Sampler
    try:
        from emitter import start_fastapi_server
        start_fastapi_server()
    except Exception as e:
        print(f"[MAIN] FastAPI server start error (non-fatal): {e}")

    try:
        from layers.hardware import start_hw_sampler
        start_hw_sampler()
    except Exception as e:
        print(f"[MAIN] Hardware sampler start error (non-fatal): {e}")

    try:
        # Just import to ensure it's available, runs on-demand
        from layers.stealth_windows import run_stealth_window_scan
    except Exception as e:
        print(f"[MAIN] Stealth windows import error (non-fatal): {e}")

    # Step 7 — VPN baseline (must happen before first network scan)
    try:
        from layers.network import set_vpn_baseline
        set_vpn_baseline()
    except Exception as e:
        print(f"[MAIN] VPN baseline error (non-fatal): {e}")

    # Step 8 — Ready message
    _print_ready(caps)


def _print_ready(caps) -> None:
    """Print the ready message listing all active detection methods."""
    active = []
    if caps.has_window_api:
        active.append("Window title monitoring")
    if caps.can_read_connections:
        active.append("Network connection table scanning")
    if caps.has_clipboard:
        active.append("Clipboard event monitoring")
    active.append("Process / DLL scanning")
    active.append("Listening port scanning")
    active.append("Model file access monitoring")
    if caps.has_nvidia:
        active.append("NVIDIA GPU utilisation")
    if caps.has_amd:
        active.append("AMD GPU monitoring")
    active.append("CPU / RAM monitoring")
    active.append("VPN activation detection")
    active.append("Encrypted DNS (DoH/DoT) detection")
    active.append("AI connection timing analysis")

    print("\n╔══════════════════════════════════════════╗")
    print("║        AI DETECTOR — READY               ║")
    print("╚══════════════════════════════════════════╝")
    print("Active detection methods:")
    for method in active:
        print(f"  ✅ {method}")
    print("\nFastAPI service on http://0.0.0.0:8002")
    print("Endpoints: POST /analyze/process  POST /analyze/network")
    print("           GET  /analyze/hardware GET  /analyze/full")
    print("           WS   /stream/system    GET  /health")
    print(f"\nEmitting JSON every 30 s to ai_detection_output.json")
    print("Press Ctrl+C to stop.\n")


# ─── Detection loop ───────────────────────────────────────────────────────────

def detection_loop() -> None:
    """Run all 5 layer scans continuously; emit every EMIT_INTERVAL seconds.

    Score scenario expectations (see Section 11 in the spec):

    Scenario: Baseline (nothing AI running)            → expected 0–15
      Browser: 0  |  Network: 0  |  Process: 0
      Behavioral: 0  |  Hardware: 0
      No layers firing → no compound multiplier.

    Scenario: ChatGPT open in browser                  → expected 45–70
      Browser: 6–10 (title + domain connection)
      Network: 4+ (long-held HTTPS connection to openai.com)
      Process: 0–2 (no local AI process)
      Behavioral: 5+ (large AI-style pastes likely)
      Hardware: 0–3 (CPU spike from browser)
      Weighted: ~50, possibly 3 layers firing → ×1.3 → ~65

    Scenario: Ollama running locally                   → expected 55–80
      Browser: 0–3 (no browser AI tab)
      Network: 0–3 (local port, no external connection)
      Process: 8–10 (ollama process + port 11434 + DLLs)
      Behavioral: 0–5 (paste activity varies)
      Hardware: 4–7 (GPU sustained >30%, RAM spike)
      Weighted: ~50, 3+ layers firing → ×1.3–1.5 → ~65–75

    Scenario: Both simultaneously                      → expected 75–100
      All layers firing at high values.
      4+ layers firing → ×1.5 multiplier.
      Evasion (if VPN/DoH active) → +15 → clamp at 100.
    """
    from config import POLL_INTERVAL_NORMAL, EMIT_INTERVAL
    from layers.browser    import run_browser_scan
    from layers.process    import run_process_scan
    from layers.hardware   import run_hardware_scan
    from layers.behavioral import run_behavioral_scan
    from layers.network    import run_network_scan
    from layers.stealth_windows import run_stealth_window_scan
    from aggregator        import add_snapshot, compute_score
    from emitter           import emit

    last_emit_time = 0.0

    while True:
        try:
            # Run all 5 scans sequentially (fast enough; avoids threading complexity)
            results = []

            for scan_fn, layer_label in [
                (run_browser_scan,        "BROWSER"),
                (run_process_scan,        "PROCESS"),
                (run_hardware_scan,       "HARDWARE"),
                (run_behavioral_scan,     "BEHAVIORAL"),
                (run_network_scan,        "NETWORK"),
                (run_stealth_window_scan, "STEALTH_WINDOWS"),
            ]:
                try:
                    result = scan_fn()
                    results.append(result)
                except Exception as e:
                    print(f"[{layer_label}] scan error: {e}")
                    # Provide a zeroed-out safe result so the snapshot is still complete
                    results.append({
                        "layer":      layer_label.lower(),
                        "score":      0,
                        "evidence":   [],
                        "confidence": 0.0,
                        "raw":        {"error": str(e)},
                    })

            add_snapshot(results)

            now = time.monotonic()
            if now - last_emit_time >= EMIT_INTERVAL:
                payload = compute_score()
                emit(payload)
                last_emit_time = now

                score    = payload.get("hardware_ai_score", 0)
                conf     = payload.get("confidence", 0)
                ev_count = len(payload.get("evidence", []))
                firing   = payload.get("layers_firing", 0)
                print(
                    f"[EMIT] Score: {score:.1f} | "
                    f"Conf: {conf:.2f} | "
                    f"Evidence: {ev_count} | "
                    f"Layers firing: {firing}"
                )

        except KeyboardInterrupt:
            print("\n[MAIN] Stopped by user.")
            sys.exit(0)
        except Exception as e:
            print(f"[MAIN] detection_loop error: {e}")
            traceback.print_exc()

        try:
            time.sleep(POLL_INTERVAL_NORMAL)
        except Exception:
            pass


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _show_consent()
    _startup()
    detection_loop()
