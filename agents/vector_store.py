import os
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from .embeddings import Embedder

class VectorStore:
    """
    Simple vector store for embeddings using numpy and pickle
    Optimized for Docker/Fargate deployment
    """
    
    def __init__(self, persist_path: str = "data/vector_store.pkl"):
        """
        Initialize vector store
        
        Args:
            persist_path (str): Path to save/load vector store data
        """
        self.embedder = Embedder()
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(exist_ok=True)
        
        # Storage for vectors and metadata
        self.vectors = []  # List of numpy arrays (embeddings)
        self.metadata = []  # List of metadata dicts for each vector
        self.dimension = None  # Embedding dimension (set on first embedding)
        
        # Load existing data if available
        self.load()
        
        print(f"✅ VectorStore initialized with {len(self.vectors)} vectors")

    def add_text(self, text: str, metadata: Dict[str, Any]) -> str:
        """
        Add text to vector store by creating embedding
        
        Args:
            text (str): Text to embed and store
            metadata (Dict): Associated metadata
            
        Returns:
            str: Generated ID for the stored vector
        """
        try:
            # Generate embedding
            embedding = self.embedder.create_embedding(text)
            if embedding is None:
                raise ValueError("Failed to create embedding")
            
            # Convert to numpy array
            vector = np.array(embedding, dtype=np.float32)
            
            # Set dimension on first vector
            if self.dimension is None:
                self.dimension = len(vector)
                print(f"📏 Set embedding dimension to {self.dimension}")
            
            # Validate dimension consistency
            if len(vector) != self.dimension:
                raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {len(vector)}")
            
            # Generate ID and add metadata
            vector_id = f"vec_{len(self.vectors)}"
            metadata_with_id = {
                'id': vector_id,
                'text': text,
                **metadata
            }
            
            # Store vector and metadata
            self.vectors.append(vector)
            self.metadata.append(metadata_with_id)
            
            print(f"➕ Added vector {vector_id} (total: {len(self.vectors)})")
            return vector_id
            
        except Exception as e:
            print(f"❌ Error adding text to vector store: {e}")
            return None
    
    def similarity_search(self, query: str, top_k: int = 5, min_similarity: float = 0.0) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using cosine similarity

        Args:
            query (str): Query text to search for
            top_k (int): Number of top results to return
            min_similarity (float): Minimum similarity threshold

        Returns:
            List[Dict]: List of results with metadata and similarity scores
        """
        try:
            if not self.vectors:
                print("⚠️  No vectors in store for search")
                return []
            
            # Create embedding for query
            query_embedding = self.embedder.create_embedding(query)
            if query_embedding is None:
                print("❌ Failed to create query embedding")
                return []
            
            query_vector = np.array(query_embedding, dtype=np.float32)
            
            # Validate dimension
            if len(query_vector) != self.dimension:
                print(f"❌ Query embedding dimension mismatch: expected {self.dimension}, got {len(query_vector)}")
                return []
            
            # Calculate cosine similarities
            similarities = []
            for i, stored_vector in enumerate(self.vectors):
                # Cosine similarity: dot product of normalized vectors
                query_norm = query_vector / np.linalg.norm(query_vector)
                stored_norm = stored_vector / np.linalg.norm(stored_vector)
                similarity = np.dot(query_norm, stored_norm)
                
                if similarity >= min_similarity:
                    similarities.append({
                        'index': i,
                        'similarity': float(similarity),
                        'metadata': self.metadata[i]
                    })
            
            # Sort by similarity (highest first) and limit results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            results = similarities[:top_k]
            
            print(f"🔍 Found {len(results)} similar vectors for query (top_k={top_k})")
            for i, result in enumerate(results):
                print(f"  {i+1}. Similarity: {result['similarity']:.3f} - {result['metadata']['text'][:50]}...")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in similarity search: {e}")
            return []
    
    def get_by_id(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Get vector metadata by ID"""
        for metadata in self.metadata:
            if metadata['id'] == vector_id:
                return metadata
        return None
    
    def clear(self):
        """Clear all vectors and metadata"""
        self.vectors = []
        self.metadata = []
        self.dimension = None
        print("🗑️  Cleared vector store")
    
    def save(self):
        """Save vector store to disk"""
        try:
            # Ensure parent directory exists
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"📁 Saving vector store to: {self.persist_path}")
            print(f"📊 Data to save: {len(self.vectors)} vectors, {len(self.metadata)} metadata entries")
            
            data = {
                'vectors': self.vectors,
                'metadata': self.metadata,
                'dimension': self.dimension
            }
            
            # Check if directory is writable
            if not os.access(self.persist_path.parent, os.W_OK):
                print(f"❌ Directory {self.persist_path.parent} is not writable!")
                print(f"📁 Directory permissions: {oct(os.stat(self.persist_path.parent).st_mode)[-3:]}")
                return
            
            with open(self.persist_path, 'wb') as f:
                pickle.dump(data, f)
            
            # Verify file was created and get size
            if os.path.exists(self.persist_path):
                file_size = os.path.getsize(self.persist_path)
                print(f"✅ Successfully saved vector store to {self.persist_path}")
                print(f"📦 File size: {file_size} bytes, {len(self.vectors)} vectors")
            else:
                print(f"❌ Vector store file was not created at {self.persist_path}")
            
        except Exception as e:
            print(f"❌ Error saving vector store: {e}")
            import traceback
            traceback.print_exc()
    
    def load(self):
        """Load vector store from disk"""
        try:
            if not self.persist_path.exists():
                print(f"📁 No existing vector store found at {self.persist_path}")
                return
            
            with open(self.persist_path, 'rb') as f:
                data = pickle.load(f)
            
            self.vectors = data.get('vectors', [])
            self.metadata = data.get('metadata', [])
            self.dimension = data.get('dimension', None)
            
            print(f"📂 Loaded vector store from {self.persist_path} ({len(self.vectors)} vectors)")
            
        except Exception as e:
            print(f"❌ Error loading vector store: {e}")
            # Reset to empty state on load failure
            self.vectors = []
            self.metadata = []
            self.dimension = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            'total_vectors': len(self.vectors),
            'dimension': self.dimension,
            'persist_path': str(self.persist_path),
            'memory_usage_mb': sum(vector.nbytes for vector in self.vectors) / (1024 * 1024) if self.vectors else 0
        }
