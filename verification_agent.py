from ..utils.confidence import ConfidenceEngine
from ..vectorstore.chroma_store import ChromaStore

class VerificationAgent:
    def __init__(self, confidence_engine: ConfidenceEngine, chroma_store: ChromaStore):
        self.confidence_engine = confidence_engine
        self.chroma_store = chroma_store

    def process(self, state: dict) -> dict:
        claim = state["extracted_claim"]
        
        # Calculate initial trust
        initial_trust = self.confidence_engine.calculate_initial_confidence(
            claim["source_reliability"], claim["verifiable"]
        )
        
        is_adversarial = claim["source_reliability"] < 0.3
        
        # Check Chroma for duplicates
        query_text = f"{claim['subject']} {claim['predicate']} {claim['object']}"
        results = self.chroma_store.search_similar(query_text, k=1)
        
        duplicate_of = None
        if results:
            doc, score = results[0]
            # Lower score is better in Chroma usually (L2 distance), but LangChain similarity_search_with_score can vary.
            # Assuming score < 0.5 implies high semantic similarity
            if score < 0.5:
                # Also check if it's the exact same subject/predicate
                if doc.metadata.get("subject", "").lower() == claim["subject"].lower() and \
                   doc.metadata.get("predicate", "").lower() == claim["predicate"].lower():
                    duplicate_of = {
                        "subject": doc.metadata.get("subject"),
                        "predicate": doc.metadata.get("predicate"),
                        "object": doc.metadata.get("object")
                    }
                    
        return {
            "initial_trust": initial_trust,
            "is_adversarial": is_adversarial,
            "duplicate_of": duplicate_of
        }
