import os
from langchain_chroma import Chroma
from .embedding_service import EmbeddingService

class ChromaStore:
    def __init__(self):
        self.persist_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'chroma_db')
        self.embedding_service = EmbeddingService()
        
        self.vectorstore = Chroma(
            collection_name="memory_claims",
            embedding_function=self.embedding_service.get_embeddings_model(),
            persist_directory=self.persist_directory
        )

    def add_claim(self, text: str, metadata: dict):
        self.vectorstore.add_texts(texts=[text], metadatas=[metadata])

    def update_claim(self, doc_id: str, text: str, metadata: dict):
        # Chroma update is done via add_texts with specific ids if needed,
        # but for our simple memory, we can just add a new entry or rely on memory.db for state.
        pass

    def search_similar(self, query: str, k: int = 5):
        # Perform similarity search
        return self.vectorstore.similarity_search_with_score(query, k=k)
