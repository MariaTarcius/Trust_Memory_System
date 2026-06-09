from ..utils.llm_client import LLMClient
from ..memory.memory_store import MemoryStore

class ContradictionAgent:
    def __init__(self, llm_client: LLMClient, memory_store: MemoryStore):
        self.llm = llm_client
        self.memory = memory_store

    def process(self, state: dict) -> dict:
        claim = state["extracted_claim"]
        duplicate_of = state["duplicate_of"]
        
        contradictions = []
        
        if duplicate_of:
            return {"contradictions": contradictions, "has_conflicts": False}
            
        # We need to see if there is an active memory with the same subject and predicate
        mem = self.memory.query(claim["subject"], claim["predicate"])
        
        if mem and mem['status'] == 'active':
            # Ask LLM if they contradict
            mem_text = f"{mem['subject']} {mem['predicate']} {mem['object']}"
            claim_text = f"{claim['subject']} {claim['predicate']} {claim['object']}"
            
            conflict_res = self.llm.detect_contradiction(mem_text, claim_text)
            if conflict_res.get("is_contradiction", False):
                contradictions.append({
                    "memory_entry": mem,
                    "type": conflict_res.get("type", "VALUE_CONFLICT"),
                    "explanation": conflict_res.get("explanation", "Detected conflict")
                })
                
        return {
            "contradictions": contradictions,
            "has_conflicts": len(contradictions) > 0
        }
