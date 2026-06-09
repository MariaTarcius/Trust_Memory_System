import os
import math
import json
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

class LLMClient:
    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN")
        self.llm_model = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct") # fallback if 3-8B not found
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
        
        if not self.hf_token:
            print("WARNING: HF_TOKEN not set in .env. LLM calls will fail.")
            
        self.client = InferenceClient(token=self.hf_token)

    def get_embedding(self, text: str) -> list[float]:
        try:
            # Using feature extraction API for embeddings
            output = self.client.feature_extraction(text, model=self.embedding_model)
            # HF returns a nested list [1, seq_len, hidden_size] or just list depending on model.
            # Usually for sentence transformers it's just the embedding, let's take the first element if nested
            import numpy as np
            emb = np.array(output)
            if len(emb.shape) > 1:
                # mean pooling if sequence length is returned
                emb = emb.mean(axis=max(0, len(emb.shape)-2))
            return emb.flatten().tolist()
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * 1024

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def semantic_similarity(self, text1: str, text2: str) -> float:
        # fallback for exact match
        if text1.strip().lower() == text2.strip().lower():
            return 1.0
            
        try:
            emb1 = self.get_embedding(text1)
            emb2 = self.get_embedding(text2)
            return self.cosine_similarity(emb1, emb2)
        except Exception as e:
            print(f"Similarity error: {e}")
            return 0.0

    def prompt_llm(self, prompt: str) -> str:
        try:
            # Using text generation API
            response = self.client.text_generation(
                prompt,
                model=self.llm_model,
                max_new_tokens=512,
                temperature=0.1,
                return_full_text=False
            )
            return response.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            return "{}" # Return empty JSON if parsing expected

    def detect_contradiction(self, claim1_text: str, claim2_text: str) -> dict:
        from src.claim_logic import detect_conflict

        parts1 = claim1_text.split(" ", 2)
        parts2 = claim2_text.split(" ", 2)
        obj1 = parts1[2] if len(parts1) > 2 else claim1_text
        obj2 = parts2[2] if len(parts2) > 2 else claim2_text
        rule_result = detect_conflict(obj1, obj2)
        if rule_result.get("is_contradiction"):
            return rule_result

        prompt = f"""
You are an expert NLI (Natural Language Inference) system.
Analyze if Claim 2 contradicts Claim 1.
Claim 1: {claim1_text}
Claim 2: {claim2_text}

Respond in strictly valid JSON format:
{{
    "is_contradiction": true/false,
    "type": "VALUE_CONFLICT" | "NEGATION" | "TEMPORAL_UPDATE" | "SUBSET_CONFLICT" | "NONE",
    "explanation": "brief reason"
}}
"""
        response = self.prompt_llm(prompt)
        try:
            cleaned = response[response.find('{'):response.rfind('}')+1]
            llm_result = json.loads(cleaned)
            if llm_result.get("is_contradiction"):
                return llm_result
        except Exception:
            pass

        return rule_result

    def generate_explanation(self, subject: str, predicate: str, object_val: str, provenance: list) -> str:
        prov_text = json.dumps(provenance, indent=2)
        prompt = f"""
Based on the following provenance history for the fact: {subject} {predicate} {object_val}, explain why the system currently believes this fact.
History: {prov_text}
Keep it concise and focus on corroboration, contradictions that were resolved, and reliability of sources.
"""
        return self.prompt_llm(prompt)
