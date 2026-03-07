"""
config.py — Single source of truth for all constants, thresholds, and settings.
All other modules import from this file; never define constants elsewhere.
"""

# ─── Poll Intervals (seconds) ─────────────────────────────────────────────────
POLL_INTERVAL_FAST   = 0.5    # clipboard, window-title polling
POLL_INTERVAL_NORMAL = 1.0    # process list, port scan
POLL_INTERVAL_SLOW   = 5.0    # GPU utilisation, disk/model-file checks

EMIT_INTERVAL = 30.0          # seconds between WebSocket + file emits

# ─── Layer Weights (must sum to 100) ─────────────────────────────────────────
WEIGHTS = {
    "browser":    35,
    "network":    25,
    "process":    20,
    "behavioral": 15,
    "hardware":    5,
}

# ─── Detection Thresholds ─────────────────────────────────────────────────────
GPU_UTIL_THRESHOLD    = 30     # % GPU utilisation above which we flag it
RAM_SPIKE_MB          = 500    # MB RSS per process above which we flag it
PASTE_CHAR_THRESHOLD  = 200    # clipboard paste size (chars) to flag
SILENCE_BURST_SECONDS = 3.0    # seconds of silence before a burst = AI paste

# ─── AI Local Server Ports ───────────────────────────────────────────────────
AI_PORTS = {
    11434: "Ollama",
    1234:  "LM Studio",
    8080:  "LocalAI",
    8888:  "Jupyter",
    5000:  "Generic AI server",
    7860:  "Gradio UI",
}

# ─── Known AI Process Names ───────────────────────────────────────────────────
AI_PROCESS_NAMES = [
    "ollama",
    "lmstudio",
    "llama-server",
    "llamafile",
    "koboldcpp",
    "textgen",
    "Jan",
    "msty",
]

# ─── Varchas Threat Process Blacklist ────────────────────────
# Maps lowercase process name fragment → (display_label, severity)
# severity is one of: 'critical', 'high'
THREAT_PROCESSES = {
    'parakeet':        ('ParakeetAI',                  'critical'),
    'interviewcoder':  ('InterviewCoder',               'critical'),
    'shadecoder':      ('ShadeCoder',                   'critical'),
    'cluely':          ('Cluely',                       'critical'),
    'interviewsolver': ('InterviewSolver',              'critical'),
    'yoodli':          ('Yoodli',                       'high'),
    'pickle':          ('Pickle AI',                    'high'),
    'ngrok':           ('Tunnel — remote helper',       'critical'),
    'anydesk':         ('Remote desktop',               'critical'),
    'teamviewer':      ('Remote desktop',               'critical'),
    'obs64':           ('OBS — virtual camera',         'high'),
    'obs32':           ('OBS — virtual camera',         'high'),
    'manycam':         ('ManyCam virtual camera',       'high'),
    'voicemeeter':     ('Audio routing for injection',  'high'),
    'ollama':          ('Local LLM server',             'high'),
    'lmstudio':        ('LM Studio local LLM',          'high'),
    'llamafile':       ('Portable LLM',                 'high'),
    'koboldcpp':       ('KoboldCpp LLM',                'high'),
}

# ─── Varchas Threat Domains ───────────────────────────────────
# Domains that indicate active cheating tools or tunneling.
# These are checked in addition to AI_DOMAINS.
THREAT_DOMAINS = {
    # Interview cheating SaaS
    'parakeet-ai.com':      'critical',
    'interviewcoder.co':    'critical',
    'cluely.ai':            'critical',
    'shadecoder.com':       'critical',
    # Tunneling / remote helper
    'ngrok.io':             'critical',
    'ngrok.com':            'critical',
    'localtunnel.me':       'critical',
    'serveo.net':           'critical',
    'pagekite.net':         'critical',
    # Remote desktop
    'anydesk.com':          'critical',
    'teamviewer.com':       'critical',
    # LLM routing
    'openrouter.ai':        'high',
    'api.together.xyz':     'high',
    'api.mistral.ai':       'high',
    'api.groq.com':         'high',
}

# ─── ETW / Stealth Window Constants (Windows only) ───────────────
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW  = 0x00000080

# ─── Hardware Monitor Settings ────────────────────────────────
HW_SAMPLE_RATE_HZ      = 10          # samples per second
HW_HISTORY_SECONDS     = 30          # seconds of history to keep
HW_HISTORY_MAXLEN      = HW_SAMPLE_RATE_HZ * HW_HISTORY_SECONDS  # = 300
GPU_SPIKE_THRESHOLD    = 70          # % GPU util = inference spike
RAM_LLM_THRESHOLD_GB   = 4.0         # GB RAM = 7B model loaded
CAUSALITY_WINDOW_SEC   = 6.0         # seconds to look back for GPU spike
                                     # before a network event

# ─── FastAPI Service Settings ─────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8002

# ─── AI-Related DLLs / Shared Libraries ──────────────────────────────────────
AI_DLLS = [
    "torch",
    "tensorflow",
    "onnxruntime",
    "cublas",
    "cudart",
    "cudnn",
    "llama",
    "whisper",
]

# ─── AI Model File Extensions ────────────────────────────────────────────────
AI_MODEL_EXTENSIONS = [
    ".gguf",
    ".pt",
    ".pth",
    ".onnx",
    ".bin",
    ".safetensors",
    ".ggml",
]

# ─── Browser Window Title Keywords ───────────────────────────────────────────
AI_WINDOW_KEYWORDS = [
    "chatgpt",
    "claude",
    "gemini",
    "copilot",
    "perplexity",
    "hugging face",
    "ollama",
    "lm studio",
    "mistral",
    "grok",
    "you.com",
    "phind",
    "poe.com",
    "character.ai",
]

# ─── Known AI API Domains ────────────────────────────────────────────────────
AI_DOMAINS = [
    "api.openai.com",
    "chat.openai.com",
    "openai.com",
    "claude.ai",
    "api.anthropic.com",
    "gemini.google.com",
    "generativelanguage.googleapis.com",
    "copilot.microsoft.com",
    "api.cohere.ai",
    "huggingface.co",
    "api.mistral.ai",
    "api.perplexity.ai",
    "stability.ai",
    "api.together.xyz",
    "api.groq.com",
    "you.com",
    "phind.com",
    "poe.com",
]

# ─── VPN / Evasion Detection ─────────────────────────────────────────────────
VPN_PROCESS_NAMES = [
    "openvpn",
    "wireguard",
    "nordvpn",
    "expressvpn",
    "mullvad",
]

DOH_PORTS = [853, 5053]       # DNS-over-HTTPS / DNS-over-TLS ports

# Known DoH/DoT provider IPs — only flag connections to these
DOH_PROVIDER_IPS = {
    "1.1.1.1", "1.0.0.1",              # Cloudflare
    "8.8.8.8", "8.8.4.4",              # Google
    "9.9.9.9", "149.112.112.112",      # Quad9
    "94.140.14.14", "94.140.15.15",    # AdGuard
    "185.228.168.9", "185.228.169.9",  # CleanBrowsing
    "76.76.2.0", "76.76.10.0",         # Alternate DNS
}

HEURISTIC_MIN_CHARS = 80      # minimum paste size (chars) to run AI-style heuristics

# ─── Output / WebSocket Settings ─────────────────────────────────────────────
WS_HOST    = "localhost"
WS_PORT    = 9999
OUTPUT_FILE = "ai_detection_output.json"
