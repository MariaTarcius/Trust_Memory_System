from src.llm_client import LLMClient
from src.memory_store import MemoryStore

class BaseAgent:
    def __init__(self, llm_client: LLMClient, memory_store: MemoryStore):
        self.llm = llm_client
        self.memory = memory_store

    def log(self, message: str):
        print(f"[{self.__class__.__name__}] {message}")
