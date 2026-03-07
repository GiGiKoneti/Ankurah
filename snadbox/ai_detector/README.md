# Varchas — README

**Varchas** is the Systems Intelligence layer of **TruthLens**, an AI cheating detection system for technical interviews. It runs as a FastAPI service on **port 8002**.

## Architecture

TruthLens has three components on the same machine:
| Component | Port | Role |
|-----------|------|------|
| GiGi | 8001 | WavLM, LNCLIP-DF, ONNX model inference |
| **Varchas** | **8002** | OS/network/hardware forensics ← this repo |
| Surakshan | 8003 | Risk scoring + orchestration |

## Features

| Layer | What it Detects |
|-------|----------------|
| **Process** | AI process names, loaded DLLs, listening ports (Ollama, LM Studio, etc.), threat process blacklist (Parakeet, InterviewCoder, Cluely, ngrok...), WMI hidden process discrepancy, model file (`.gguf`, `.pt`, `.onnx`) access |
| **Network** | VPN activation (7 prefix types), DoH/DoT mid-session (4-condition check), long-held AI connections, reverse-DNS exact matching against 30+ AI domains, upload bandwidth spikes, TLS SNI inspection |
| **Hardware** | NVIDIA GPU spike (pynvml), AMD GPU (sysfs/WMI), 10Hz background sampler, RAM model-load pattern (> 2GB growth in 30s), disk read spike detection, CPU thread explosion, GPU→network causality chain |
| **Behavioral** | Clipboard large paste (>500 chars), AI-style text heuristics (5 signals), pynput keystroke timing (never key values), low backspace rate pattern, Q&A latency std deviation analysis |
| **Browser** | Window title keyword scan (word-boundary regex), connection reverse-DNS exact match against AI domains, screen color analysis of top 100px for ChatGPT/Claude/Gemini/Copilot UI signatures |
| **Peripheral** | USB device class scan (HID/Video/Network), Bluetooth earpiece/phone detection, display count and remote desktop detection, hypervisor/VM detection |
| **Stealth Windows** | Windows-only ETW-based layered/transparent/toolwindow detection |

## Self-Exclusion

**Varchas never flags its own siblings.** The `_is_internal_service()` function in `capability.py` checks:
1. `TRUTHLENS_SERVICE` environment variable (set to `'gigi'`, `'varchas'`, or `'surakshan'`)
2. Cmdline script name heuristic + port match

Internal ports `{8001, 8002, 8003}` are skipped in all network and process scans.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Status, uptime, active monitors list |
| POST | `/analyze/process` | Process + stealth layer scan |
| POST | `/analyze/network` | Network + browser scan |
| GET | `/analyze/hardware` | Hardware layer scan |
| POST | `/analyze/peripheral` | USB/BT/display/VM scan |
| GET | `/analyze/full` | All layers + aggregated score |
| WS | `/stream/system` | Real-time ForensicEvent stream at 100ms |

### WebSocket Message Types

```json
{"type": "forensic_event", "data": {...}}   // immediate critical event
{"type": "score_update",   "data": {...}}   // periodic aggregate
```

## Installation

```bash
# Clone and enter project
cd /home/bitwisebrain/snadbox/ai_detector

# Activate existing venv
source ../venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running Varchas

```bash
cd /home/bitwisebrain/snadbox/ai_detector
source ../venv/bin/activate
python main.py
```

Varchas will:
1. Prompt for monitoring consent
2. Print the capability report
3. Start all background monitors
4. Print confirmation: `http://0.0.0.0:8002`
5. Run the detection loop (logs every 30s)

## Output Format

`/analyze/full` returns:
```json
{
  "timestamp": 1741337387.4,
  "session_id": "uuid-...",
  "hardware_ai_score": 42.5,
  "confidence": 0.92,
  "capability_mode": "admin",
  "os": "Linux",
  "layer_breakdown": {
    "browser": 7.0,
    "network": 0.0,
    "process": 5.0,
    "behavioral": 0.0,
    "hardware": 0.0,
    "peripheral": 0.0
  },
  "layers_firing": 2,
  "evasion_flags": [],
  "evidence": ["AI process 'ollama' (PID 1234)", "..."],
  "ready_for_ensemble": true
}
```

## Configuration

All constants are in `config.py`. Key thresholds:

| Constant | Default | Purpose |
|----------|---------|---------|
| `GPU_SPIKE_THRESHOLD` | 80% | GPU utilisation = LLM inference |
| `PASTE_CHAR_THRESHOLD` | 500 | Clipboard paste size to flag |
| `LONG_CONN_SEC` | 5s | AI connection duration to flag |
| `DISK_READ_SPIKE_MB` | 500 MB | Model loading from disk |
| `TYPING_BURST_WPM` | 200 | WPM above which = likely paste |
| `LATENCY_AI_STD` | 0.3s | Std deviation < this = AI timing |

## File Structure

```
ai_detector/
├── config.py              # All constants (single source of truth)
├── capability.py          # Hardware/OS detection + _is_internal_service()
├── aggregator.py          # Rolling window scoring + compound bonuses
├── api.py                 # FastAPI service + WebSocket + ForensicEvent queue
├── main.py                # Entry point: consent → startup → detection loop
├── emitter.py             # Legacy file writer (preserved for compatibility)
├── requirements.txt
├── shared/
│   └── schemas.py         # ForensicEvent Pydantic model
├── layers/
│   ├── process.py         # Process/DLL/port/threat/WMI/model-file scanning
│   ├── network.py         # VPN/DoH/DNS/bandwidth/TLS SNI/long-conn scanning
│   ├── hardware.py        # GPU/CPU/RAM/disk/causality chain detection
│   ├── behavioral.py      # Clipboard/keyboard/latency analysis
│   ├── browser.py         # Window titles/connections/screen color analysis
│   ├── peripheral.py      # USB/Bluetooth/display/VM detection
│   └── stealth_windows.py # Windows ETW stealth overlay detection
└── db/
    ├── __init__.py
    └── ai_domains.py      # AI domain IP cache resolver
```
