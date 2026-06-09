from typing import TypedDict, Optional, List, Dict
from langgraph.graph import StateGraph, END
import json

from ..agents.extraction_agent import ExtractionAgent
from ..agents.verification_agent import VerificationAgent
from ..agents.contradiction_agent import ContradictionAgent
from ..agents.curator_agent import CuratorAgent
from ..utils.llm_client import LLMClient
from ..memory.memory_store import MemoryStore
from ..memory.change_log import ChangeLog
from ..utils.confidence import ConfidenceEngine
from ..vectorstore.chroma_store import ChromaStore

class WorkflowState(TypedDict):
    raw_claim: dict
    extracted_claim: Optional[dict]
    initial_trust: float
    is_adversarial: bool
    duplicate_of: Optional[dict]
    contradictions: List[dict]
    has_conflicts: bool
    final_decision: str

class TAMISWorkflow:
    def __init__(self):
        # Initialize dependencies
        self.llm = LLMClient()
        self.memory = MemoryStore(capacity=20)
        self.change_log = ChangeLog()
        self.confidence_engine = ConfidenceEngine()
        self.chroma_store = ChromaStore()

        # Initialize Agents
        self.extractor = ExtractionAgent()
        self.verifier = VerificationAgent(self.confidence_engine, self.chroma_store)
        self.contradictor = ContradictionAgent(self.llm, self.memory)
        self.curator = CuratorAgent(self.memory, self.change_log, self.confidence_engine, self.chroma_store)

        # Build Graph
        builder = StateGraph(WorkflowState)
        
        builder.add_node("extract", self._node_extract)
        builder.add_node("verify", self._node_verify)
        builder.add_node("contradiction", self._node_contradiction)
        builder.add_node("curate", self._node_curate)
        
        builder.set_entry_point("extract")
        builder.add_edge("extract", "verify")
        builder.add_edge("verify", "contradiction")
        builder.add_edge("contradiction", "curate")
        builder.add_edge("curate", END)
        
        self.graph = builder.compile()

    # Node wrappers to adapt StateGraph
    def _node_extract(self, state: WorkflowState):
        res = self.extractor.process(state)
        return res

    def _node_verify(self, state: WorkflowState):
        res = self.verifier.process(state)
        return res

    def _node_contradiction(self, state: WorkflowState):
        res = self.contradictor.process(state)
        return res

    def _node_curate(self, state: WorkflowState):
        res = self.curator.process(state)
        return res

    def process_claim(self, raw_claim: dict) -> dict:
        initial_state = {
            "raw_claim": raw_claim,
            "extracted_claim": None,
            "initial_trust": 0.0,
            "is_adversarial": False,
            "duplicate_of": None,
            "contradictions": [],
            "has_conflicts": False,
            "final_decision": ""
        }
        
        result = self.graph.invoke(initial_state)
        return result
