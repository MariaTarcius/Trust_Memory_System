from ..utils.llm_client import LLMClient
from ..memory.memory_store import MemoryStore

class ExplainabilityAgent:
    def __init__(self, llm_client: LLMClient, memory_store: MemoryStore):
        self.llm = llm_client
        self.memory = memory_store

    def explain(self, subject: str, predicate: str) -> dict:
        mem = self.memory.query(subject, predicate)
        if not mem:
            return {"error": "Memory not found."}
            
        prov = mem.get("provenance_history", [])
        obj = mem.get("object", "")
        
        # Call LLM to generate natural language explanation
        explanation = self.llm.generate_explanation(subject, predicate, obj, prov)
        
        return {
            "subject": subject,
            "predicate": predicate,
            "object": obj,
            "confidence": mem.get("confidence", 0.0),
            "status": mem.get("status", "unknown"),
            "llm_explanation": explanation,
            "provenance_timeline": prov
        }
