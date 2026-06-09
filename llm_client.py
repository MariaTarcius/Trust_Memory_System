import os
import json
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from langchain_core.prompts import PromptTemplate

load_dotenv()

class LLMClient:
    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN")
        self.llm_model = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        
        # We use InferenceClient directly for chat_completion because the 'nscale' provider 
        # specifically requires 'conversational' task rather than 'text-generation',
        # which can cause issues with standard LangChain HuggingFaceEndpoint wrappers.
        self.client = InferenceClient(token=self.hf_token)

    def prompt_llm(self, prompt: str) -> str:
        try:
            # Use chat_completion (conversational) to bypass the 'text-generation' error
            messages = [{"role": "user", "content": prompt}]
            response = self.client.chat_completion(
                messages,
                model=self.llm_model,
                max_tokens=512,
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            return "{}"

    def detect_contradiction(self, claim1_text: str, claim2_text: str) -> dict:
        prompt_template = PromptTemplate.from_template(
            "You are an expert NLI system.\n"
            "Analyze if Claim 2 contradicts Claim 1.\n"
            "Claim 1: {claim1}\n"
            "Claim 2: {claim2}\n\n"
            "Respond in strictly valid JSON format:\n"
            "{{\n"
            '    "is_contradiction": true/false,\n'
            '    "type": "VALUE_CONFLICT" | "NEGATION" | "TEMPORAL_UPDATE" | "SUBSET_CONFLICT" | "NONE",\n'
            '    "explanation": "brief reason"\n'
            "}}"
        )
        prompt = prompt_template.format(claim1=claim1_text, claim2=claim2_text)
        response = self.prompt_llm(prompt)
        
        try:
            cleaned = response[response.find('{'):response.rfind('}')+1]
            return json.loads(cleaned)
        except Exception:
            return {"is_contradiction": False, "type": "NONE", "explanation": "Failed to parse."}

    def generate_explanation(self, subject: str, predicate: str, object_val: str, provenance: list) -> str:
        prov_text = json.dumps(provenance, indent=2)
        prompt_template = PromptTemplate.from_template(
            "Based on the following provenance history for the fact: {subject} {predicate} {object_val}, "
            "explain why the system currently believes this fact.\n"
            "History: {history}\n"
            "Keep it concise."
        )
        prompt = prompt_template.format(
            subject=subject, predicate=predicate, object_val=object_val, history=prov_text
        )
        return self.prompt_llm(prompt)
