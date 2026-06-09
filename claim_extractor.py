from datetime import datetime
import json
from src.models import Claim
from src.agents.base_agent import BaseAgent

class ClaimExtractorAgent(BaseAgent):
    def process(self, raw_json: dict) -> Claim:
        # Handle missing timestamp edge case
        ts = raw_json.get("timestamp")
        if not ts:
            ts = datetime.utcnow().isoformat() + "Z"
            self.log(f"Assigned default timestamp to claim {raw_json.get('id')}")

        claim = Claim(
            id=raw_json.get("id"),
            timestamp=ts,
            source_id=raw_json.get("source_id"),
            source_reliability=float(raw_json.get("source_reliability", 0.5)),
            verifiable=raw_json.get("verifiable", "NOT VERIFIABLE"),
            label=raw_json.get("label", "NOT ENOUGH INFO"),
            claim=raw_json.get("claim", ""),
            subject=raw_json.get("subject", ""),
            predicate=raw_json.get("predicate", ""),
            object=raw_json.get("object"),
            notes=raw_json.get("notes", "")
        )
        self.log(f"Extracted claim {claim.id}: {claim.subject} {claim.predicate} {claim.object}")
        return claim
