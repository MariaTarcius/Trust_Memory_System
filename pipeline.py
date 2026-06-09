import json
import os
from datetime import datetime
from src.llm_client import LLMClient
from src.memory_store import MemoryStore
from src.confidence import ConfidenceEngine
from src.agents.claim_extractor import ClaimExtractorAgent
from src.agents.verifier import VerifierAgent
from src.agents.contradiction import ContradictionAgent
from src.agents.curator import CuratorAgent

class Pipeline:
    def __init__(self, data_path: str, memory_path: str, log_path: str):
        self.data_path = data_path
        self.memory_path = memory_path
        self.log_path = log_path
        
        self.llm = LLMClient()
        self.memory = MemoryStore(capacity=20)
        self.confidence_engine = ConfidenceEngine()
        
        self.extractor = ClaimExtractorAgent(self.llm, self.memory)
        self.verifier = VerifierAgent(self.llm, self.memory, self.confidence_engine)
        self.contradiction = ContradictionAgent(self.llm, self.memory)
        self.curator = CuratorAgent(self.llm, self.memory, self.confidence_engine)
        
        # State
        self.claims = []
        self.current_idx = 0

    def load_data(self):
        if not os.path.exists(self.data_path):
            print(f"Data file not found at {self.data_path}")
            return
            
        raw_claims = []
        with open(self.data_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    raw_claims.append(json.loads(line))
                    
        # Sort by timestamp, nulls at the end
        def sort_key(c):
            ts = c.get('timestamp')
            if not ts:
                return "9999-12-31T23:59:59Z"
            return ts
            
        raw_claims.sort(key=sort_key)
        self.claims = raw_claims
        print(f"Loaded {len(self.claims)} claims.")

    def step(self):
        if self.current_idx >= len(self.claims):
            print("No more claims to process.")
            return False
            
        raw_claim = self.claims[self.current_idx]
        self.current_idx += 1
        
        print(f"\n--- Processing Claim {raw_claim.get('id')} ---")
        
        # 1. Extract
        claim = self.extractor.process(raw_claim)
        
        # 2. Verify
        verified_data = self.verifier.process(claim)
        
        # 3. Detect Contradictions
        conflict_data = self.contradiction.process(verified_data)
        
        # 4. Curate
        self.curator.process(conflict_data)
        
        # Save state incrementally
        self.save()
        return True

    def run_all(self):
        self.load_data()
        while self.step():
            pass
        print("Pipeline finished.")

    def save(self):
        self.memory.save(self.memory_path, self.log_path)

    def load(self):
        self.memory.load(self.memory_path, self.log_path)
