from typing import Optional
from src.models import Claim, MemoryEntry, MemoryStatus, ActionType
from src.agents.base_agent import BaseAgent
from src.confidence import ConfidenceEngine
from src.llm_client import LLMClient
from src.memory_store import MemoryStore


class CuratorAgent(BaseAgent):
    REVISE_THRESHOLD = 1.02
    REJECT_THRESHOLD = 0.88

    def __init__(self, llm_client: LLMClient, memory_store: MemoryStore, confidence_engine: ConfidenceEngine):
        super().__init__(llm_client, memory_store)
        self.confidence_engine = confidence_engine

    def _is_filler_claim(self, claim: Claim) -> bool:
        label = (claim.label or "").upper().replace(" ", "_")
        return label == "NOT_ENOUGH_INFO"

    def _should_revise(
        self,
        new_trust: float,
        mem_trust: float,
        conflict_type: str,
        claim: Optional[Claim] = None,
    ) -> bool:
        if new_trust > mem_trust * self.REVISE_THRESHOLD:
            return True
        if conflict_type in ("VALUE_CONFLICT", "TEMPORAL_UPDATE", "NEGATION") and claim:
            if claim.source_reliability >= 0.85 and new_trust >= mem_trust * 0.95:
                return True
            if conflict_type == "TEMPORAL_UPDATE" and new_trust >= mem_trust * 0.98:
                return True
        return False

    def _effective_trust(self, claim: Claim, initial_trust: float, mem: Optional[MemoryEntry]) -> float:
        trust = initial_trust
        if mem and mem.revision_count >= 3:
            trust = self.confidence_engine.apply_oscillation_penalty(trust, mem.revision_count)
        if claim.label == "REFUTES":
            trust *= 0.85
        return trust

    def _memory_confidence(self, mem: MemoryEntry, claim: Claim) -> float:
        decay = self.confidence_engine.get_time_decay(mem.last_updated, claim.timestamp)
        return mem.confidence * decay

    def _conflict_baseline_confidence(self, mem: MemoryEntry, claim: Claim) -> float:
        """Strip corroboration inflation so authoritative corrections can still revise memory."""
        corroboration_bonus = min(0.04 * max(mem.corroboration_count - 1, 0), 0.12)
        baseline = max(mem.confidence - corroboration_bonus, 0.5)
        decay = self.confidence_engine.get_time_decay(mem.last_updated, claim.timestamp)
        return baseline * decay

    def _merge_memory(self, claim: Claim, mem: MemoryEntry, reason: str):
        new_conf = self.confidence_engine.apply_corroboration(
            mem.confidence, mem.corroboration_count
        )
        self.memory.merge(
            subject=claim.subject,
            predicate=claim.predicate,
            new_source=claim.source_id,
            new_confidence=new_conf,
            claim_id=claim.id,
            reason=reason,
        )
        self.log(f"MERGED {claim.id}: {reason}")

    def _accept_new(self, claim: Claim, initial_trust: float, reason: str):
        entry = MemoryEntry(
            subject=claim.subject,
            predicate=claim.predicate,
            object=claim.object,
            confidence=initial_trust,
            status=MemoryStatus.ACTIVE,
            sources=[claim.source_id],
            first_seen=claim.timestamp,
            last_updated=claim.timestamp,
            provenance_history=[{
                "timestamp": claim.timestamp,
                "action": ActionType.ACCEPTED.value,
                "triggering_claim_id": claim.id,
                "confidence_before": 0.0,
                "confidence_after": initial_trust,
                "explanation": reason,
            }],
        )
        self.memory.store(entry, claim.id, reason)
        self.log(f"ACCEPTED {claim.id}: {reason}")

    def _revise_memory(
        self,
        claim: Claim,
        mem: MemoryEntry,
        new_trust: float,
        conflict_type: str,
        reason: str,
    ):
        self.memory.revise(
            subject=claim.subject,
            predicate=claim.predicate,
            new_object=claim.object,
            new_confidence=new_trust,
            new_source=claim.source_id,
            claim_id=claim.id,
            reason=f"{reason} (Type: {conflict_type})",
        )
        self.log(f"REVISED {claim.id}: {reason}")

    def _downgrade_memory(self, mem: MemoryEntry, claim: Claim, reason: str):
        new_conf = self.confidence_engine.apply_contradiction_penalty(
            mem.confidence, [claim.source_reliability]
        )
        self.memory.downgrade(mem.subject, mem.predicate, new_conf, claim.id, reason)
        self.log(f"DOWNGRADED memory for {mem.subject} {mem.predicate}: {reason}")

    def _reject_claim(self, claim_id: str, reason: str):
        self.memory.reject(claim_id, reason)
        self.log(f"REJECTED {claim_id}: {reason}")

    def process(self, conflict_data: dict):
        verified_data = conflict_data["verified_data"]
        claim: Claim = verified_data["claim"]
        initial_trust = verified_data["initial_trust"]
        is_adversarial = verified_data["is_adversarial"]
        duplicate_of = verified_data["duplicate_of"]
        corroborates = verified_data.get("corroborates")

        contradictions = conflict_data["contradictions"]
        has_conflicts = conflict_data["has_conflicts"]

        self.log(f"Curating claim {claim.id} (Trust: {initial_trust:.2f})")

        # 1. Exact or semantic duplicates -> MERGE
        if duplicate_of:
            self._merge_memory(
                claim,
                duplicate_of,
                f"Corroborated existing memory by duplicate claim from {claim.source_id}",
            )
            return

        # 2. Compatible corroboration (subset/detail alignment) -> MERGE
        if corroborates:
            self._merge_memory(
                claim,
                corroborates,
                f"Corroborated existing memory with compatible detail from {claim.source_id}",
            )
            return

        # 3. Adversarial claim contradicting active memory -> REJECT
        if is_adversarial and has_conflicts:
            self._reject_claim(
                claim.id,
                f"Adversarial claim rejected (low trust source {claim.source_reliability:.2f} "
                f"contradicts active memory)",
            )
            return

        # 4. Conflicts require revise / downgrade / reject decisions
        if has_conflicts:
            conflict = contradictions[0]
            mem: MemoryEntry = conflict["memory_entry"]
            conflict_type = conflict["type"]

            new_trust = self._effective_trust(claim, initial_trust, mem)
            mem_trust = self._conflict_baseline_confidence(mem, claim)

            if self._should_revise(new_trust, mem_trust, conflict_type, claim):
                self._revise_memory(
                    claim,
                    mem,
                    new_trust,
                    conflict_type,
                    f"Revised memory due to stronger evidence from {claim.source_id}",
                )
                return

            stored_trust = self._memory_confidence(mem, claim)
            if new_trust < stored_trust * self.REJECT_THRESHOLD:
                if is_adversarial or new_trust < 0.35:
                    self._reject_claim(
                        claim.id,
                        "Claim weaker than existing active memory or from adversarial source.",
                    )
                else:
                    self._downgrade_memory(
                        mem,
                        claim,
                        f"Downgraded existing memory after weaker contradictory claim from {claim.source_id}",
                    )
                    self._reject_claim(
                        claim.id,
                        "Incoming claim rejected because existing memory remains more credible.",
                    )
                return

            # Equal-confidence band -> DOWNGRADE memory + REJECT incoming claim
            self._downgrade_memory(
                mem,
                claim,
                "Equal confidence conflict with existing memory; downgrading stored belief.",
            )
            self._reject_claim(claim.id, "Equal confidence conflict unresolved; incoming claim rejected.")
            return

        # 5. Same key exists but no explicit conflict flagged -> treat as implicit conflict
        existing = self.memory.query(claim.subject, claim.predicate)
        if (
            existing
            and existing.status in (MemoryStatus.ACTIVE, MemoryStatus.LOW_CONFIDENCE)
            and existing.object != claim.object
        ):
            mem_trust = self._conflict_baseline_confidence(existing, claim)
            new_trust = self._effective_trust(claim, initial_trust, existing)
            if self._should_revise(new_trust, mem_trust, "IMPLICIT_CONFLICT", claim):
                self._revise_memory(
                    claim,
                    existing,
                    new_trust,
                    "IMPLICIT_CONFLICT",
                    f"Revised implicit conflict using stronger claim from {claim.source_id}",
                )
            elif new_trust < mem_trust * self.REJECT_THRESHOLD:
                self._reject_claim(claim.id, "Implicit conflict: existing memory is stronger.")
            else:
                self._downgrade_memory(existing, claim, "Implicit equal-confidence conflict.")
                self._reject_claim(claim.id, "Implicit equal-confidence conflict unresolved.")
            return

        # 6. Low-trust filler claims are stored with low confidence to trigger eviction later
        if is_adversarial and initial_trust < 0.15 and self._is_filler_claim(claim):
            reason = (
                f"Accepted low-confidence filler from {claim.source_id} "
                f"(candidate for future eviction)"
            )
            entry = MemoryEntry(
                subject=claim.subject,
                predicate=claim.predicate,
                object=claim.object,
                confidence=initial_trust,
                status=MemoryStatus.LOW_CONFIDENCE,
                sources=[claim.source_id],
                first_seen=claim.timestamp,
                last_updated=claim.timestamp,
                provenance_history=[{
                    "timestamp": claim.timestamp,
                    "action": ActionType.ACCEPTED.value,
                    "triggering_claim_id": claim.id,
                    "confidence_before": 0.0,
                    "confidence_after": initial_trust,
                    "explanation": reason,
                }],
            )
            self.memory.store(entry, claim.id, reason)
            self.log(f"ACCEPTED (low confidence) {claim.id}: {reason}")
            return

        if is_adversarial and initial_trust < 0.15:
            self._reject_claim(
                claim.id,
                f"Rejected low-trust adversarial claim from {claim.source_id}",
            )
            return

        # 7. Fresh fact with no conflicts -> ACCEPT
        reason = f"Accepted new fact from {claim.source_id}"
        self._accept_new(claim, initial_trust, reason)
