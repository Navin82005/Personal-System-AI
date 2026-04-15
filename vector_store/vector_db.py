import chromadb
from chromadb.utils import embedding_functions
import requests
from config import settings
from ingestion.chunking import DocumentChunk
from utils.logging import setup_logger

logger = setup_logger("vector_db")

class VectorDB:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.vector_db_path)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model_name
        )
        self.collection = self.client.get_or_create_collection(
            name="personal_system",
            embedding_function=self.embedding_fn
        )
        print(f"DEBUG: VectorDB initialized at {settings.vector_db_path}")
        logger.info(f"Initialized ChromaDB at {settings.vector_db_path}")

    def _get_embedding(self, text: str) -> chromadb.Embeddings:
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text
            }
        )
        response.raise_for_status() # Good practice to catch API errors
        
        embedding = response.json()["embedding"]
        return embedding

    def add_chunks(self, chunks: list[DocumentChunk], source: str):
        print(f"DEBUG: VectorDB add_chunks: received {len(chunks)} chunks for source: {source}")
        if not chunks:
            print("DEBUG: VectorDB add_chunks: no chunks to add, returning")
            return
            
        documents = []
        embedding = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk.text)
            embedding.append(self._get_embedding(chunk.text))
            metadata = chunk.metadata.copy()
            metadata["source"] = source
            metadatas.append(metadata)
            ids.append(f"{source}_{i}")
            
        # Add to collection (Chroma handles embedding under the hood via the embedding_fn)
        self.collection.add(
            embeddings=embedding,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"DEBUG: VectorDB add_chunks: successfully added {len(chunks)} chunks to collection")
        logger.info(f"Added {len(chunks)} chunks to vector store from {source}")

    def search(self, query: str, top_k: int = 3, where: dict | None = None) -> chromadb.QueryResult:
        query_embedding = self._get_embedding(query)
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": top_k
        }
        if where:
            kwargs["where"] = where
            
        print(f"DEBUG: VectorDB search kwargs: {kwargs}")
        results = self.collection.query(**kwargs)
        print(f"DEBUG: VectorDB search results count: {len(results.get('ids', [[]])[0])}")
        return results

    def get_all_sources(self):
        print("DEBUG: VectorDB get_all_sources called")
        data = self.collection.get(include=["metadatas"])
        sources = set()
        for meta in data.get("metadatas", []):
            if "source" in meta:
                sources.add(meta["source"])
        print(f"DEBUG: VectorDB found sources: {sources}")
        return list(sources)
        
    def has_file(self, filename: str) -> bool:
        """
        Check if a particular file is indexed in the database metadata.
        Uses exact string mapping of 'filename' metadata.
        """
        print(f"DEBUG: VectorDB has_file called for target filename: {filename}")
        # Chroma where filter allows efficient metadata lookup
        results = self.collection.get(
            where={"file_name": filename},
            limit=1
        )
        self.get_all_data()
        self.get_all_sources()
        print("DEBUG: Vector db sources")
        has_file_result = len(results.get("ids", [])) > 0
        print(f"DEBUG: VectorDB has_file result for target filename '{filename}': {has_file_result}")
        return has_file_result

    def get_all_metadata(self):
        """
        Retrieves a list of unique metadata dictionaries for all indexed files.
        """
        data = self.collection.get(include=["metadatas"])
        unique_metadata = {}
        for meta in data.get("metadatas", []):
            if not meta:
                continue
            source = meta.get("source")
            if source and source not in unique_metadata:
                unique_metadata[source] = meta
                
        return unique_metadata

    def get_all_data(self):
        """
        Retrieves all documents, metadatas, and ids stored in the vector database.
        """
        # Include documents, metadatas (and potentially embeddings if needed)
        data = self.collection.get(include=["documents", "metadatas"])
        print(f"DEBUG: VectorDB get_all_data called -> {data}")
        return data

