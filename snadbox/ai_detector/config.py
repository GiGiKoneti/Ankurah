"""
config.py — Single source of truth for all constants, thresholds, and settings.
All other modules import from this file; never define constants elsewhere.
"""

# ─── Poll Intervals (seconds) ─────────────────────────────────────────────────
POLL_INTERVAL_FAST   = 0.1    # 100ms clipboard, window-title polling, WS tick
POLL_INTERVAL_NORMAL = 1.0    # process list, port scan
POLL_INTERVAL_SLOW   = 5.0    # GPU utilisation, disk/model-file checks

EMIT_INTERVAL = 30.0          # seconds between score summary log lines

# ─── Hardware Monitor Settings ────────────────────────────────────────────────
HW_SAMPLE_RATE_HZ   = 10           # samples per second
HW_HISTORY_SECONDS  = 30           # seconds of history to keep
HW_HISTORY_MAXLEN   = HW_SAMPLE_RATE_HZ * HW_HISTORY_SECONDS  # = 300

# ─── Detection Thresholds ─────────────────────────────────────────────────────
GPU_UTIL_THRESHOLD    = 50     # % GPU utilisation above which we flag it
GPU_SPIKE_THRESHOLD   = 80     # % GPU util = inference spike (causality chain)
RAM_SPIKE_MB          = 2000   # MB RSS per process above which we flag it
RAM_LLM_THRESHOLD_GB  = 5.0    # GB RAM indicating a 7B model loaded
PASTE_CHAR_THRESHOLD  = 500    # clipboard paste size (chars) to flag
SILENCE_BURST_SECONDS = 3.0    # seconds of silence before a burst = AI paste
CAUSALITY_WINDOW_SEC  = 3.0    # seconds to look for GPU→network causality chain
LONG_CONN_SEC         = 5.0    # seconds a connection to AI IP is considered long
DISK_READ_SPIKE_MB    = 500    # MB read in < 10s = model loading from disk
THREAD_EXPLOSION      = 32     # process thread count above which we flag it
TYPING_BURST_WPM      = 200    # sudden burst WPM above this = likely paste
LATENCY_AI_STD        = 0.3    # std deviation < this = AI-consistent response timing
LATENCY_HUMAN_STD     = 0.8    # std deviation > this = human-like variance
MIN_LATENCY_SAMPLES   = 3      # minimum samples before latency scoring
HEURISTIC_MIN_CHARS   = 150    # minimum paste size (chars) to run AI-style heuristics

# ─── Self-Exclusion (CRITICAL: Never flag TruthLens siblings) ─────────────────
INTERNAL_PORTS    = {8001, 8002, 8003}       # GiGi, Varchas, Surakshan
INTERNAL_HOSTS    = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}
TRUTHLENS_ENV_KEY = 'TRUTHLENS_SERVICE'      # env var marking internal services
INTERNAL_SERVICES = {'gigi', 'varchas', 'surakshan'}
SYSTEM_DNS_IPS    = {'127.0.0.1', '::1', '127.0.0.53', '168.63.129.16'}

# ─── Layer Weights (must sum to 100) ─────────────────────────────────────────
WEIGHTS = {
    "browser":    30,
    "network":    25,
    "process":    20,
    "behavioral": 10,
    "hardware":    5,
    "peripheral": 10,
}

# ─── ETW / Stealth Window Constants (Windows only) ───────────────────────────
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW  = 0x00000080

# ─── AI Local Server Ports ───────────────────────────────────────────────────
AI_PORTS = {
    11434: "Ollama",
    1234:  "LM Studio",
    8080:  "LocalAI",
    8888:  "Jupyter",
    7860:  "Gradio UI",
    5000:  "Flask LLM",
    3000:  "Node LLM proxy",
}

# ─── Known AI Process Names ───────────────────────────────────────────────────
AI_PROCESS_NAMES = [
    "ollama",
    "llama",
    "lmstudio",
    "llamafile",
    "koboldcpp",
    "localai",
    "gpt4all",
    "jan",
    "textgen",
    "msty",
]

# ─── Varchas Threat Process Blacklist ─────────────────────────────────────────
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
    'anydesk':         ('Remote desktop — AnyDesk',     'critical'),
    'teamviewer':      ('Remote desktop — TeamViewer',  'critical'),
    'obs64':           ('OBS — virtual camera 64-bit',  'high'),
    'obs32':           ('OBS — virtual camera 32-bit',  'high'),
    'manycam':         ('ManyCam virtual camera',       'high'),
    'voicemeeter':     ('Audio routing for injection',  'high'),
    'ollama':          ('Local LLM server',             'high'),
    'lmstudio':        ('LM Studio local LLM',          'high'),
    'llamafile':       ('Portable LLM',                 'high'),
    'koboldcpp':       ('KoboldCpp LLM',                'high'),
    'discord':         ('Discord — possible screen share', 'high'),
    'zoom':            ('Zoom — possible screen sharing', 'high'),
}

# ─── Varchas Threat Domains ───────────────────────────────────────────────────
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

# ─── Known AI API Domains ─────────────────────────────────────────────────────
AI_DOMAINS = [
    # OpenAI / ChatGPT
    "api.openai.com",
    "chat.openai.com",
    "openai.com",
    # Anthropic / Claude
    "claude.ai",
    "api.anthropic.com",
    # Google
    "gemini.google.com",
    "generativelanguage.googleapis.com",
    "bard.google.com",
    # Microsoft
    "copilot.microsoft.com",
    # Cohere
    "api.cohere.com",
    "api.cohere.ai",
    # Mistral
    "api.mistral.ai",
    # Perplexity
    "api.perplexity.ai",
    "perplexity.ai",
    # Groq
    "api.groq.com",
    # Together
    "api.together.xyz",
    # OpenRouter
    "openrouter.ai",
    # HuggingFace
    "huggingface.co",
    # Replicate
    "replicate.com",
    # You.com / Phind
    "you.com",
    "phind.com",
    # Stability AI
    "stability.ai",
    # Poe
    "poe.com",
    # Interview cheating SaaS (also in THREAT_DOMAINS for severity)
    "parakeet-ai.com",
    "interviewcoder.co",
    "cluely.ai",
    # Tunneling
    "ngrok.io",
    "ngrok.com",
    "localtunnel.me",
    "serveo.net",
    # Remote desktop
    "anydesk.com",
    "teamviewer.com",
]

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

# ─── AI Model File Extensions ─────────────────────────────────────────────────
AI_MODEL_EXTENSIONS = [
    ".gguf",
    ".pt",
    ".pth",
    ".onnx",
    ".bin",
    ".safetensors",
    ".ggml",
]

# ─── Browser Window Title Keywords ────────────────────────────────────────────
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
    "interviewcoder",
    "cluely",
    "parakeet",
    "gpt",
    "llama",
    "bard",
]

# ─── AI Interface Color Signatures (RGB tuples) ────────────────────────────────
# Used by browser screen color analysis (top 100px tab bar capture)
AI_INTERFACE_COLORS = {
    "chatgpt_dark":  (33, 33, 33),
    "claude_purple": (124, 58, 237),
    "gemini_blue":   (26, 115, 232),
    "copilot":       (0, 120, 212),
}

# ─── VPN / Evasion Detection ──────────────────────────────────────────────────
VPN_IFACE_PREFIXES = ["tun", "wg", "ppp", "tap", "vpn"]

VPN_PROCESS_NAMES = [
    "openvpn",
    "wireguard",
    "nordvpn",
    "expressvpn",
    "mullvad",
    "tailscale",
    "zerotier",
    "hamachi",
]

DOH_PORTS = {853, 5053}    # DNS-over-HTTPS / DNS-over-TLS ports

# Known DoH/DoT provider IPs — only flag new connections to these
DOH_PROVIDER_IPS = {
    # Cloudflare
    "1.1.1.1", "1.0.0.1",
    "2606:4700:4700::1111", "2606:4700:4700::1001",
    # Google
    "8.8.8.8", "8.8.4.4",
    "2001:4860:4860::8888", "2001:4860:4860::8844",
    # Quad9
    "9.9.9.9", "149.112.112.112",
    "2620:fe::fe", "2620:fe::9",
    # AdGuard
    "94.140.14.14", "94.140.15.15",
    # CleanBrowsing
    "185.228.168.9", "185.228.169.9",
    # Alternate DNS
    "76.76.2.0", "76.76.10.0",
    # Microsoft (Azure/Windows DoH)
    "168.63.129.16",
    "13.107.4.52", "13.107.5.52",
}

# ─── FastAPI Service Settings ─────────────────────────────────────────────────
API_HOST    = "0.0.0.0"
API_PORT    = 8002
OUTPUT_FILE = "ai_detection_output.json"

# ─── Output / WebSocket Settings (legacy — kept for emitter.py) ───────────────
WS_HOST = "localhost"
WS_PORT = 9999
