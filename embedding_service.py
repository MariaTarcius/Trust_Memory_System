import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

class EmbeddingService:
    def __init__(self):
        # Using sentence-transformers locally instead of inference API to avoid 500 errors
        self.model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
        
        # We use Langchain's HuggingFaceEmbeddings which downloads the model locally
        # This completely bypasses the HF Inference API 500 errors
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_name)

    def get_embeddings_model(self):
        return self.embeddings
