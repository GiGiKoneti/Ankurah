"""
shared/schemas.py — Pydantic models shared across all TruthLens components.

ForensicEvent is the canonical event object emitted by all three components
(GiGi :8001, Varchas :8002, Surakshan :8003) to the fusion engine.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import time


class ForensicEvent(BaseModel):
    """A single forensic evidence event from one layer of one component.

    Fields
    ------
    timestamp   : Unix epoch float — when the event was created
    source      : Component name: 'gigi', 'varchas', or 'surakshan'
    layer       : Detection layer: 'process', 'network', 'hardware',
                  'behavioral', 'browser', 'peripheral', 'stealth_windows'
    signal      : Machine-readable signal name (no spaces), e.g. 'gpu_spike'
    value       : Normalised confidence value [0.0, 1.0]
    raw         : Arbitrary dict with raw evidence for downstream fusion
    severity    : 'low', 'medium', 'high', or 'critical'
    description : Human-readable one-line summary of this event
    session_id  : Optional session UUID for event correlation
    """

    timestamp:   float         = Field(default_factory=time.time)
    source:      str
    layer:       str
    signal:      str
    value:       float         = Field(ge=0.0, le=1.0)
    raw:         Dict[str, Any] = Field(default_factory=dict)
    severity:    str           = "medium"
    description: str           = ""
    session_id:  Optional[str] = None
