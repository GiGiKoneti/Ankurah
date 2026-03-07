"""
aggregator.py — Maintains a rolling 30-second window of layer scan snapshots
and computes a weighted ensemble score with compound bonuses and evasion penalties.

The output dict is the formal contract with the parent ensemble system.
"""

import collections
import time
import threading
import uuid
from typing import List, Dict, Any

from config import WEIGHTS, EMIT_INTERVAL
from capability import caps

# ─── Session identity ─────────────────────────────────────────────────────────
SESSION_ID: str = str(uuid.uuid4())

# ─── Rolling window (thread-safe) ────────────────────────────────────────────
# One deque entry = one full pass of all 5 layers.
# 60 entries × 0.5s fast tick ≈ 30 seconds of history.
_snapshot_window: collections.deque = collections.deque(maxlen=60)
_window_lock      = threading.Lock()


def add_snapshot(layer_results: List[Dict[str, Any]]) -> None:
    """Append one full set of layer scan results to the rolling window."""
    try:
        snapshot = {
            "timestamp": time.time(),
            "layers":    {r["layer"]: r for r in layer_results},
        }
        with _window_lock:
            _snapshot_window.append(snapshot)
    except Exception as e:
        print(f"[AGGREGATOR] add_snapshot error: {e}")


def compute_score() -> Dict[str, Any]:
    """Compute the weighted ensemble AI score over the current rolling window.

    Returns the full output dict satisfying the parent-ensemble JSON contract.
    """
    try:
        with _window_lock:
            snapshots = list(_snapshot_window)

        n = len(snapshots)

        # Accumulate per-layer sum of scores
        layer_sums:  Dict[str, float] = {k: 0.0 for k in WEIGHTS}
        layer_counts: Dict[str, int]  = {k: 0   for k in WEIGHTS}
        all_evidence: List[str]       = []

        for snap in snapshots:
            for layer_name in WEIGHTS:
                result = snap["layers"].get(layer_name)
                if result is None:
                    continue
                layer_sums[layer_name]   += result.get("score", 0)
                layer_counts[layer_name] += 1
                # Collect evidence from newest snapshot only (avoid duplication)
                if snap is snapshots[-1]:
                    all_evidence.extend(result.get("evidence", []))

        # Step 1 — Average each layer's score over the window
        layer_avgs: Dict[str, float] = {}
        for layer_name in WEIGHTS:
            count = layer_counts[layer_name]
            layer_avgs[layer_name] = (
                layer_sums[layer_name] / count if count > 0 else 0.0
            )

        # Step 2 — Weighted sum (layer_avg / 10) × weight → 0-100 scale
        weighted_sum = sum(
            (layer_avgs[lname] / 10.0) * WEIGHTS[lname]
            for lname in WEIGHTS
        )

        # Step 3 — Count layers "firing" (avg score ≥ 5)
        layers_firing = sum(1 for avg in layer_avgs.values() if avg >= 5.0)
        if layers_firing >= 4:
            weighted_sum *= 1.5
        elif layers_firing >= 3:
            weighted_sum *= 1.3

        # Step 4 — Evasion penalty
        evasion_flags: List[str] = []
        try:
            from layers.network import get_evasion_flags
            evasion_flags = get_evasion_flags()
            if evasion_flags:
                evasion_bonus = min(len(evasion_flags) * 7, 15)
                weighted_sum += evasion_bonus
        except Exception as e:
            print(f"[AGGREGATOR] evasion flag fetch error: {e}")

        # Step 5 — Confidence adjustment
        # Base confidence: average of per-layer confidences from latest snapshot
        base_confidence = 1.0
        if snapshots:
            latest = snapshots[-1]
            conf_values = [
                latest["layers"][lname].get("confidence", 1.0)
                for lname in WEIGHTS
                if lname in latest["layers"]
            ]
            if conf_values:
                base_confidence = sum(conf_values) / len(conf_values)

        if not caps.is_admin:
            base_confidence *= 0.85

        # Step 6 — Clamp
        final_score  = max(0.0, min(100.0, weighted_sum))
        confidence   = max(0.0, min(1.0, base_confidence))
        ready        = n >= 10

        return {
            "timestamp":        time.time(),
            "session_id":       SESSION_ID,
            "hardware_ai_score": round(final_score, 2),
            "confidence":       round(confidence, 3),
            "capability_mode":  "admin" if caps.is_admin else "user",
            "os":               caps.os_name,
            "layer_breakdown":  {k: round(layer_avgs[k], 2) for k in WEIGHTS},
            "layers_firing":    layers_firing,
            "evasion_flags":    evasion_flags,
            "evidence":         all_evidence[:50],   # cap at 50 to keep JSON readable
            "ready_for_ensemble": ready,
        }

    except Exception as e:
        print(f"[AGGREGATOR] compute_score error: {e}")
        # Return a safe default that won't crash the ensemble consumer
        return {
            "timestamp":          time.time(),
            "session_id":         SESSION_ID,
            "hardware_ai_score":  0.0,
            "confidence":         0.0,
            "capability_mode":    "user",
            "os":                 caps.os_name,
            "layer_breakdown":    {k: 0.0 for k in WEIGHTS},
            "layers_firing":      0,
            "evasion_flags":      [],
            "evidence":           [],
            "ready_for_ensemble": False,
        }
