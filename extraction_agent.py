from datetime import datetime

class ExtractionAgent:
    def process(self, state: dict) -> dict:
        raw = state["raw_claim"]
        ts = raw.get("timestamp")
        if not ts:
            ts = datetime.utcnow().isoformat() + "Z"
            
        claim = {
            "id": raw.get("id", ""),
            "timestamp": ts,
            "source_id": raw.get("source_id", "Unknown"),
            "source_reliability": float(raw.get("source_reliability", 0.5)),
            "verifiable": raw.get("verifiable", "NOT VERIFIABLE"),
            "claim": raw.get("claim", ""),
            "subject": raw.get("subject", ""),
            "predicate": raw.get("predicate", ""),
            "object": raw.get("object", "")
        }
        
        return {"extracted_claim": claim}
