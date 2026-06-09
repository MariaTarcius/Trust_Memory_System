import math
from datetime import datetime

class ConfidenceEngine:
    def __init__(self):
        pass
        
    def calculate_initial_confidence(self, source_reliability: float, verifiable: str) -> float:
        weight = 1.0 if verifiable == "VERIFIABLE" else 0.5
        # Adversarial dampening
        if source_reliability < 0.3:
            weight *= 0.5
        
        return min(source_reliability * weight, 1.0)
        
    def apply_corroboration(self, base_confidence: float, corroboration_count: int) -> float:
        boost = min(0.04 * corroboration_count, 0.15)
        return min(base_confidence + boost, 0.96)
        
    def apply_contradiction_penalty(self, confidence: float, contradicting_reliabilities: list[float]) -> float:
        penalty = sum([r * 0.3 for r in contradicting_reliabilities])
        return max(confidence * (1 - penalty), 0.0)
        
    def apply_oscillation_penalty(self, confidence: float, revision_count: int) -> float:
        if revision_count >= 3:
            # If it's flip-flopped a lot, trust it less
            return confidence * 0.8
        return confidence
        
    def get_time_decay(self, claim_timestamp: str, current_timestamp: str) -> float:
        if not claim_timestamp or not current_timestamp:
            return 1.0
        try:
            t1 = datetime.fromisoformat(claim_timestamp.replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(current_timestamp.replace('Z', '+00:00'))
            diff_days = (t2 - t1).days
            if diff_days > 0:
                decay = 1.0 - (diff_days * 0.01)
                return max(decay, 0.5) # Max 50% decay
        except Exception:
            pass
        return 1.0
