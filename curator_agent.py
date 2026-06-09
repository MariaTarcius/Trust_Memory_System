from ..memory.memory_store import MemoryStore
from ..memory.change_log import ChangeLog
from ..utils.confidence import ConfidenceEngine
from ..vectorstore.chroma_store import ChromaStore

class CuratorAgent:
    def __init__(self, memory_store: MemoryStore, change_log: ChangeLog, confidence_engine: ConfidenceEngine, chroma_store: ChromaStore):
        self.memory = memory_store
        self.change_log = change_log
        self.confidence_engine = confidence_engine
        self.chroma_store = chroma_store

    def process(self, state: dict) -> dict:
        claim = state["extracted_claim"]
        initial_trust = state["initial_trust"]
        is_adversarial = state["is_adversarial"]
        duplicate_of = state["duplicate_of"]
        contradictions = state["contradictions"]
        has_conflicts = state["has_conflicts"]
        
        action_taken = ""
        
        # 1. Handle Duplicates
        if duplicate_of:
            mem = self.memory.query(claim["subject"], claim["predicate"])
            if mem:
                new_conf = self.confidence_engine.apply_corroboration(mem['confidence'], mem['corroboration_count'])
                reason = f"Corroborated existing memory by semantic duplicate from {claim['source_id']}"
                self.memory.merge(claim["subject"], claim["predicate"], claim["source_id"], new_conf, claim["id"], claim["timestamp"], reason)
                self.change_log.log(claim["id"], claim["timestamp"], "MERGED", reason, mem['object'], mem['object'], new_conf - mem['confidence'])
                action_taken = "MERGED"
                return {"final_decision": action_taken}
                
        # 2. Handle Adversarial + Conflicts
        if is_adversarial and has_conflicts:
            reason = f"Adversarial claim rejected (Low trust source {claim['source_reliability']} contradicts active memory)"
            self.change_log.log(claim["id"], claim["timestamp"], "REJECTED", reason, None, None, 0.0)
            return {"final_decision": "REJECTED"}
            
        # 3. Handle Conflicts
        if has_conflicts:
            conflict = contradictions[0]
            mem = conflict["memory_entry"]
            ctype = conflict["type"]
            
            decayed_mem_conf = self.confidence_engine.get_time_decay(mem['last_updated'], claim["timestamp"]) * mem['confidence']
            
            new_trust = initial_trust
            if mem['revision_count'] >= 3:
                new_trust = self.confidence_engine.apply_oscillation_penalty(new_trust, mem['revision_count'])
                
            if new_trust > decayed_mem_conf * 1.1:
                reason = f"Revised memory due to stronger evidence from {claim['source_id']} (Type: {ctype})"
                self.memory.revise(claim["subject"], claim["predicate"], claim["object"], new_trust, claim["source_id"], claim["id"], claim["timestamp"], reason)
                self.change_log.log(claim["id"], claim["timestamp"], "REVISED", reason, mem['object'], claim['object'], new_trust - mem['confidence'])
                
                # Also update Chroma
                text = f"{claim['subject']} {claim['predicate']} {claim['object']}"
                meta = {"subject": claim['subject'], "predicate": claim['predicate'], "object": claim['object']}
                self.chroma_store.add_claim(text, meta)
                return {"final_decision": "REVISED"}
            elif new_trust < decayed_mem_conf * 0.9:
                reason = "Claim weaker than existing active memory. Rejected."
                self.change_log.log(claim["id"], claim["timestamp"], "REJECTED", reason, None, None, 0.0)
                return {"final_decision": "REJECTED"}
            else:
                reason = "Equal confidence conflict with existing memory. Downgrading existing."
                new_mem_conf = self.confidence_engine.apply_contradiction_penalty(mem['confidence'], [claim['source_reliability']])
                self.memory.downgrade(mem['subject'], mem['predicate'], new_mem_conf, claim["id"], claim["timestamp"], reason)
                self.change_log.log(claim["id"], claim["timestamp"], "DOWNGRADED", reason, mem['object'], mem['object'], new_mem_conf - mem['confidence'])
                return {"final_decision": "DOWNGRADED_EXISTING_REJECTED_NEW"}
                
        # 4. New Fact
        reason = f"Accepted new fact from {claim['source_id']}"
        self.memory.store(
            subject=claim["subject"],
            predicate=claim["predicate"],
            obj=claim["object"],
            confidence=initial_trust,
            status="active",
            sources=[claim["source_id"]],
            timestamp=claim["timestamp"],
            claim_id=claim["id"],
            reason=reason
        )
        self.change_log.log(claim["id"], claim["timestamp"], "ACCEPTED", reason, None, claim["object"], initial_trust)
        
        # Add to Chroma
        text = f"{claim['subject']} {claim['predicate']} {claim['object']}"
        meta = {"subject": claim['subject'], "predicate": claim['predicate'], "object": claim['object']}
        self.chroma_store.add_claim(text, meta)
        
        return {"final_decision": "ACCEPTED"}
