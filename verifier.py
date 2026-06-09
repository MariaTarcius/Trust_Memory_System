from typing import Optional
from src.models import Claim, MemoryEntry
from src.agents.base_agent import BaseAgent
from src.confidence import ConfidenceEngine
from src.claim_logic import objects_are_duplicate, is_corroboration, detect_conflict
from src.llm_client import LLMClient
from src.memory_store import MemoryStore


class VerifierAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient, memory_store: MemoryStore, confidence_engine: ConfidenceEngine):
        super().__init__(llm_client, memory_store)
        self.confidence_engine = confidence_engine

    def _find_matching_memory(self, claim: Claim) -> Optional[MemoryEntry]:
        for mem in self.memory.get_all_active():
            if mem.subject.lower() != claim.subject.lower():
                continue
            if mem.predicate.lower() != claim.predicate.lower():
                continue
            return mem
        return None

    def process(self, claim: Claim) -> dict:
        initial_trust = self.confidence_engine.calculate_initial_confidence(
            claim.source_reliability, claim.verifiable
        )

        is_adversarial = claim.source_reliability < 0.3
        if is_adversarial:
            self.log(
                f"Flagged {claim.id} as potentially adversarial "
                f"(low trust source: {claim.source_reliability})"
            )

        duplicate_of = None
        corroborates = None
        matching_memory = self._find_matching_memory(claim)

        if matching_memory and claim.object and matching_memory.object:
            if objects_are_duplicate(matching_memory.object, claim.object):
                duplicate_of = matching_memory
                self.log(
                    f"Found duplicate for {claim.id} -> existing memory '{matching_memory.object}'"
                )
            elif is_corroboration(matching_memory.object, claim.object):
                corroborates = matching_memory
                self.log(
                    f"Found corroboration for {claim.id} -> existing memory '{matching_memory.object}'"
                )
            else:
                rule_conflict = detect_conflict(matching_memory.object, claim.object)
                if not rule_conflict.get("is_contradiction"):
                    sim = self.llm.semantic_similarity(matching_memory.object, claim.object)
                    if sim > 0.92 and not rule_conflict.get("is_contradiction"):
                        duplicate_of = matching_memory
                        self.log(
                            f"Found semantic duplicate via embedding for {claim.id} "
                            f"(similarity={sim:.2f})"
                        )
                    elif sim > 0.80 and is_corroboration(matching_memory.object, claim.object):
                        corroborates = matching_memory
                        self.log(
                            f"Found semantic corroboration via embedding for {claim.id} "
                            f"(similarity={sim:.2f})"
                        )

        return {
            "claim": claim,
            "initial_trust": initial_trust,
            "is_adversarial": is_adversarial,
            "duplicate_of": duplicate_of,
            "corroborates": corroborates,
            "matching_memory": matching_memory,
        }
