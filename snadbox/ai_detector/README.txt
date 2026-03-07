================================================================================
AI DETECTION SYSTEM — README
Hardware & Network Layer v1.0
================================================================================

WHAT THIS TOOL MONITORS
------------------------
This tool monitors the following activity on the local machine only. All data
stays local — nothing is transmitted to any external server.

  • Window titles of all open applications (to detect AI chat interfaces)
  • Network connections (IP addresses only — no packet content is inspected)
  • Running processes and names of loaded libraries/DLLs
  • GPU utilisation and VRAM usage (NVIDIA and AMD GPUs)
  • CPU utilisation per process
  • RAM (memory) usage per process
  • Clipboard paste events: size and writing-style only (content is hashed,
    NOT stored or transmitted)
  • File open events for AI model file types (.gguf, .pt, .onnx, etc.)
  • VPN process activation and network interface changes
  • Encrypted DNS (DoH/DoT) connection detection

This is the hardware and network detection layer of a larger multi-layer AI
detection ensemble. It does NOT perform audio or video surveillance of any kind.


HOW TO RUN IT
-------------
On the machine being monitored:

  1. Double-click ai_detector.exe (Windows) or run ./ai_detector (Linux/Mac)
     in a terminal.

  2. Read the consent notice displayed on screen.

  3. Type YES and press Enter to proceed.

  4. The tool runs in the background. A one-line summary is printed to the
     console every 30 seconds.

  5. Press Ctrl+C at any time to stop the tool cleanly.

No installation is required beyond running the executable. No Python
installation is needed on the target machine.


HOW TO WHITELIST IN WINDOWS DEFENDER AND COMMON AV TOOLS
---------------------------------------------------------
Some antivirus tools may flag the executable because it monitors processes and
network connections — standard behaviour for security software. To whitelist:

  Windows Defender:
  1. Open Windows Security → Virus & threat protection → Manage settings.
  2. Under Exclusions, click "Add or remove exclusions".
  3. Add "File" exclusion and select ai_detector.exe.

  Malwarebytes:
  1. Open Malwarebytes → Settings → Allow List.
  2. Click "Add exclusion" → "Exclude a file or folder".
  3. Select ai_detector.exe.

  ESET / Bitdefender / Norton / Kaspersky:
  1. Open the AV application → Settings or Quarantine management.
  2. Find the "Exclusions" or "Trusted applications" section.
  3. Add ai_detector.exe as a trusted or excluded file.

If Windows SmartScreen blocks the app on first run, click "More info" then
"Run anyway". This appears for unsigned executables.


PORT 9999 — FIREWALL CONFIGURATION
------------------------------------
The tool broadcasts a JSON score every 30 seconds via WebSocket on localhost
port 9999 (or 10000/10001 if 9999 is already in use). This traffic is local
only and does not require internet access.

To allow the tool through the Windows Firewall:
  1. Open Windows Defender Firewall → Advanced Settings.
  2. Select "Inbound Rules" → "New Rule".
  3. Choose "Port" → TCP → Specific port: 9999.
  4. Select "Allow the connection" and apply to all profiles.
  5. Name the rule "AI Detector WebSocket" and finish.

Linux (ufw):
  sudo ufw allow 9999/tcp

The actual port used is printed on startup:
  [EMITTER] WebSocket server listening on ws://localhost:9999


OUTPUT FILE — ai_detection_output.json
---------------------------------------
A JSON file is written every 30 seconds to ai_detection_output.json in the
same directory as the executable. This file is always written regardless of
network or WebSocket status and serves as a fallback output.

The file contains:

  timestamp           Unix timestamp of this snapshot
  session_id          Unique identifier for this run (UUID4)
  hardware_ai_score   Weighted AI likelihood score (0–100)
  confidence          Detection confidence (0.0–1.0)
  capability_mode     "admin" or "user" (affects confidence weighting)
  os                  Operating system name
  layer_breakdown     Per-layer average scores (browser, network, process,
                      behavioral, hardware), each 0–10
  layers_firing       Number of layers with score >= 5 (0–5)
  evasion_flags       List of detected evasion events (VPN, DoH)
  evidence            List of specific detection events this period
  ready_for_ensemble  True when enough data has been collected (>= 10 samples)

The hardware_ai_score is weighted at 30% in the parent ensemble system.
A score of 0–15 indicates no AI activity. 50+ indicates likely AI activity.
75+ indicates high-confidence AI activity.


CONTACT
-------
Project maintainer: [YOUR NAME / ORGANISATION]
Email:              [YOUR EMAIL]
Project repository: [YOUR REPO URL]

For issues or false-positive reports, please include the ai_detection_output.json
file from the session in question.
================================================================================
