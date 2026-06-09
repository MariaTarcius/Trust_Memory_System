import os
from src.llm_client import LLMClient

client = LLMClient()
sim = client.semantic_similarity("Startup A raised $5M in 2021", "Startup A raised 5 million dollars in 2021")
print(f"Similarity: {sim}")

conflict = client.detect_contradiction("Startup A raised $5M in 2021", "Startup A raised $8M in 2021")
print(f"Conflict: {conflict}")
