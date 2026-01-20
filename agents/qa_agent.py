import os
import uuid
from datetime import datetime
from typing import List, Dict, Any
import re
from .vector_store import VectorStore
from .ollama_client import get_ollama_client

class QAAgent:
    """Agent responsible for question answering using RAG approach with Ollama"""

    def __init__(self, session_id: str = None, user_id: str = None):
        """Initialize the QA Agent for local single-user deployment"""
        try:
            self.client = get_ollama_client()
            self.model = os.getenv('OLLAMA_MODEL', 'qwen2.5:14b')
            self.session_id = session_id
            self.user_id = user_id or "local_user"

            # Storage for documents and their metadata
            self.documents = []  # List of {'text': str, 'title': str, 'chunks': List[str]}

            # Initialize vector store (single global store for local deployment)
            vector_store_path = "data/vector_store.pkl"
            print(f"📁 Using global vector store: {vector_store_path}")

            self.vector_store = VectorStore(persist_path=vector_store_path)

            print(f"✅ QAAgent initialized successfully (local mode)")

        except Exception as e:
            print(f"❌ Error initializing QAAgent: {e}")
            raise
    
    def add_document(self, text: str, title: str = "Document") -> bool:
        """
        Add a document to the knowledge base (supports multiple documents with user isolation)
        
        Args:
            text (str): Document text
            title (str): Document title
            
        Returns:
            bool: Success status
        """
        try:
            if not text or len(text.strip()) < 10:
                print("⚠️  Document too short to add")
                return False
            
            # For multi-user isolation, load existing data first
            if not hasattr(self.vector_store, 'vectors') or not self.vector_store.vectors:
                print("📂 Loading existing vector store...")
                self.vector_store.load()
                
            # Clean up old documents for this user (keep max 5 per user)
            self._cleanup_user_documents()
            
            # Clean and chunk the text
            cleaned_text = self._clean_text(text)
            chunks = self._chunk_text(cleaned_text)
            
            if not chunks:
                print("⚠️  No chunks created from document")
                return False
            
            # Generate unique document ID
            doc_id = str(uuid.uuid4())
            upload_time = datetime.now().isoformat()
            
            # Store document with user information
            document = {
                'doc_id': doc_id,
                'user_id': self.user_id,
                'text': cleaned_text,
                'title': title,
                'chunks': chunks,
                'upload_time': upload_time
            }
            self.documents.append(document)
            
            # Add chunks to vector store with user metadata
            for chunk_index, chunk in enumerate(chunks):
                metadata = {
                    'user_id': self.user_id,
                    'doc_id': doc_id,
                    'chunk_index': chunk_index,
                    'title': title,
                    'doc_title': title,
                    'upload_time': upload_time,
                    'text': chunk  # Store full chunk text for context reconstruction
                }
                self.vector_store.add_text(chunk, metadata)
            
            # Save vector store
            self.vector_store.save()
            
            user_doc_count = self._count_user_documents()
            print(f"✅ Added document '{title}' with {len(chunks)} chunks for user {self.user_id}")
            print(f"👤 User now has {user_doc_count} documents in vector store")
            return True
            
        except Exception as e:
            print(f"❌ Error adding document: {e}")
            return False
    
    def answer_question(self, question: str) -> str:
        """
        Answer a question using the stored documents
        
        Args:
            question (str): User question
            
        Returns:
            str: Generated answer
        """
        try:
            if not question or len(question.strip()) < 3:
                return "Please provide a valid question."
            
            # Check if we have vectors (this is the real indicator of available content)
            if not self.vector_store.vectors:
                return "No documents have been uploaded yet. Please upload a document first, then ask your question."
            
            print(f"❓ Processing question: {question}")
            print(f"📚 Available documents: {len(self.documents)}")
            print(f"📄 Available chunks: {len(self.vector_store.vectors)}")
            
            # Get relevant context
            relevant_context = self._get_relevant_context(question)
            
            if not relevant_context:
                return "I couldn't find relevant information in the uploaded documents to answer your question."
            
            # Generate answer using OpenAI
            answer = self._generate_answer(question, relevant_context)
            
            print(f"✅ Generated answer for question")
            return answer
            
        except Exception as e:
            error_msg = f"Error answering question: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def _chunk_text(self, text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text (str): Text to chunk
            chunk_size (int): Size of each chunk
            overlap (int): Overlap between chunks
            
        Returns:
            List[str]: List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending within last 100 chars
                for i in range(min(100, chunk_size)):
                    if text[end - i - 1] in '.!?':
                        end = end - i
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            
            # Prevent infinite loop
            if start >= len(text):
                break
        
        return chunks
    
    def _get_vector_stats(self):
        """Get vector store statistics"""
        stats = self.vector_store.get_stats()
        print(f"📊 Vector Store Stats: {stats['total_vectors']} vectors, {stats['dimension']} dims, {stats['memory_usage_mb']:.1f}MB")
    
    def _get_relevant_context(self, question: str, top_k: int = 3) -> str:
        """
        Simple context retrieval - use vector store data directly
        
        Args:
            question (str): User question
            top_k (int): Number of top chunks to return (unused in simple mode)
            
        Returns:
            str: Combined relevant context
        """
        try:
            print(f"🔍 Getting context for: '{question}'")
            print(f"📋 In-memory documents: {len(self.documents)}")
            print(f"📄 Vector store chunks: {len(self.vector_store.vectors) if hasattr(self.vector_store, 'vectors') else 0}")
            
            # Use vector store data directly if in-memory documents are empty
            if not self.documents and hasattr(self.vector_store, 'metadata') and self.vector_store.metadata:
                print("🔄 Using vector store data since in-memory documents are empty")
                
                # Group chunks by document (single-user mode)
                doc_chunks = {}
                for metadata in self.vector_store.metadata:
                    doc_title = metadata.get('doc_title', metadata.get('title', 'Unknown'))
                    if doc_title not in doc_chunks:
                        doc_chunks[doc_title] = []
                    doc_chunks[doc_title].append(metadata.get('text', ''))
                
                if doc_chunks:
                    context_parts = []
                    for doc_title, chunks in doc_chunks.items():
                        # Combine chunks for this document
                        full_text = ' '.join(chunks)
                        context_parts.append(f"Document: {doc_title}\n{full_text}")
                    
                    context = "\n\n---\n\n".join(context_parts)
                    print(f"✅ Returning context from vector store: {len(context)} characters from {len(doc_chunks)} documents")
                    return context
            
            # Fallback to in-memory documents if available
            if self.documents:
                context_parts = []
                for doc in self.documents:
                    if doc.get('text'):
                        context_parts.append(f"Document: {doc.get('title', 'Unknown')}\n{doc['text']}")
                
                if context_parts:
                    context = "\n\n---\n\n".join(context_parts)
                    print(f"✅ Returning context from memory: {len(context)} characters from {len(context_parts)} documents")
                    return context
            
            print("❌ No documents available in memory or vector store")
            return ""
            
        except Exception as e:
            print(f"❌ Error getting context: {e}")
            return ""
    
    def _keyword_search(self, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Enhanced keyword-based search with better matching
        
        Args:
            question (str): User question
            top_k (int): Number of results to return
            
        Returns:
            List[Dict]: Search results with metadata
        """
        try:
            import re
            question_lower = question.lower()
            
            # Extract keywords and create search patterns
            stop_words = {'when', 'where', 'what', 'who', 'how', 'why', 'is', 'are', 'was', 'were', 'the', 'a', 'an', 'do', 'does', 'did'}
            words = re.findall(r'\b\w+\b', question_lower)
            keywords = [word for word in words if word not in stop_words and len(word) > 2]
            
            # Add common variations and synonyms
            expanded_keywords = keywords.copy()
            
            # Question-specific keyword expansion
            if 'established' in keywords or 'founded' in keywords:
                expanded_keywords.extend(['established', 'founded', 'created', 'started', 'began'])
            if 'play' in keywords and ('where' in question_lower or 'stadium' in question_lower):
                expanded_keywords.extend(['stadium', 'venue', 'field', 'ballpark', 'home'])
            if 'yankees' in keywords:
                expanded_keywords.extend(['yankee', 'new york yankees'])
            
            print(f"🔤 Enhanced keyword search for: {keywords}")
            print(f"🔍 Expanded keywords: {expanded_keywords}")
            
            results = []
            
            # Search through vector store metadata
            if self.vector_store.metadata:
                for i, metadata in enumerate(self.vector_store.metadata):
                    if metadata.get('user_id') == self.user_id or not self.user_id:
                        text_lower = metadata.get('text', '').lower()
                        score = 0
                        matched_keywords = []
                        
                        # Score based on keyword matches
                        for keyword in expanded_keywords:
                            count = text_lower.count(keyword)
                            if count > 0:
                                score += count * (2.0 if keyword in keywords else 1.0)  # Higher weight for original keywords
                                matched_keywords.append(keyword)
                        
                        if score > 0:
                            results.append({
                                'similarity': score,
                                'metadata': metadata,
                                'index': i,
                                'matched_keywords': matched_keywords
                            })
            
            # Also search through full documents if vector search fails
            if not results and self.documents:
                print("🔍 Searching full documents with keywords")
                for doc_idx, doc in enumerate(self.documents):
                    if doc.get('text'):
                        text_lower = doc['text'].lower()
                        score = 0
                        matched_keywords = []
                        
                        for keyword in expanded_keywords:
                            count = text_lower.count(keyword)
                            if count > 0:
                                score += count * (2.0 if keyword in keywords else 1.0)
                                matched_keywords.append(keyword)
                        
                        if score > 0:
                            # Create pseudo-metadata for document
                            results.append({
                                'similarity': score,
                                'metadata': {
                                    'text': doc['text'][:2000],  # Limit to first 2000 chars for display
                                    'title': doc.get('title', 'Document'),
                                    'user_id': self.user_id
                                },
                                'matched_keywords': matched_keywords
                            })
            
            # Sort by score and return top results
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            if results:
                print(f"📊 Keyword search found {len(results)} matches")
                for i, result in enumerate(results[:3]):  # Show top 3
                    print(f"  🎯 Match {i+1}: score={result['similarity']}, keywords={result.get('matched_keywords', [])}")
            
            return results[:top_k]
            
        except Exception as e:
            print(f"❌ Enhanced keyword search error: {e}")
            return []
    
    
    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generate answer using Ollama with the provided context

        Args:
            question (str): User question
            context (str): Relevant context

        Returns:
            str: Generated answer
        """
        system_prompt = """You are a helpful AI assistant that answers questions based on provided context.

Instructions:
1. ALWAYS try to find the answer in the provided context first
2. If the information exists in the context, provide it directly and confidently
3. Extract specific facts, dates, numbers, and details from the context
4. Be direct and specific - don't say "the context doesn't specify" if the information is there
5. Only say information is not available if it truly cannot be found in the context"""

        print(f"🔍 ANSWER GENERATION DEBUG:")
        print(f"  📝 Context length: {len(context)} characters")
        print(f"  🎯 Question: {question}")
        print(f"  📄 Context preview: {context[:500]}...")

        user_prompt = f"""Context:
{context}

Question: {question}

Please answer the question based on the context provided above."""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            answer = self.client.chat(
                messages=messages,
                temperature=0.1,
                top_p=0.95
            )

            return answer.strip()
            
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def _cleanup_user_documents(self, max_docs_per_user: int = 5):
        """Remove oldest documents for current user if they exceed the limit"""
        if not self.user_id or not hasattr(self.vector_store, 'metadata'):
            return
            
        # Get all user documents sorted by upload time
        user_docs = []
        for i, metadata in enumerate(self.vector_store.metadata):
            if metadata.get('user_id') == self.user_id:
                user_docs.append((i, metadata))
        
        # Group by document ID and get unique documents
        doc_times = {}
        for _, metadata in user_docs:
            doc_id = metadata.get('doc_id')
            upload_time = metadata.get('upload_time', '')
            if doc_id and doc_id not in doc_times:
                doc_times[doc_id] = upload_time
        
        # If user has too many documents, remove oldest ones
        if len(doc_times) >= max_docs_per_user:
            sorted_docs = sorted(doc_times.items(), key=lambda x: x[1])  # Sort by time
            docs_to_remove = sorted_docs[:len(sorted_docs) - max_docs_per_user + 1]
            
            for doc_id_to_remove, _ in docs_to_remove:
                self._remove_document_by_id(doc_id_to_remove)
                print(f"🗑️  Removed old document {doc_id_to_remove} for user {self.user_id}")
    
    def _remove_document_by_id(self, doc_id: str):
        """Remove all chunks of a specific document"""
        if not hasattr(self.vector_store, 'metadata'):
            return
            
        # Find indices to remove (in reverse order to avoid index shifting)
        indices_to_remove = []
        for i, metadata in enumerate(self.vector_store.metadata):
            if metadata.get('doc_id') == doc_id:
                indices_to_remove.append(i)
        
        # Remove from vector store
        for i in reversed(indices_to_remove):
            if i < len(self.vector_store.vectors):
                self.vector_store.vectors.pop(i)
                self.vector_store.metadata.pop(i)
        
        # Remove from documents list
        self.documents = [doc for doc in self.documents if doc.get('doc_id') != doc_id]
    
    def _count_user_documents(self) -> int:
        """Count unique documents for current user"""
        if not self.user_id or not hasattr(self.vector_store, 'metadata'):
            return 0
            
        user_doc_ids = set()
        for metadata in self.vector_store.metadata:
            if metadata.get('user_id') == self.user_id and metadata.get('doc_id'):
                user_doc_ids.add(metadata['doc_id'])
        
        return len(user_doc_ids)

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the QA agent (filtered by user in multi-user mode)"""
        vector_stats = self.vector_store.get_stats()
        
        # Count documents and chunks for current user
        if self.user_id and hasattr(self.vector_store, 'metadata'):
            user_doc_count = self._count_user_documents()
            user_chunk_count = sum(1 for meta in self.vector_store.metadata 
                                 if meta.get('user_id') == self.user_id)
            
            return {
                'documents_count': user_doc_count,
                'chunks_count': user_chunk_count,
                'vectors_ready': user_chunk_count > 0,
                'ready_for_questions': user_chunk_count > 0,
                'embedding_dimension': vector_stats['dimension'],
                'memory_usage_mb': vector_stats['memory_usage_mb'],
                'user_id': self.user_id
            }
        else:
            # Fallback to original behavior for non-user mode
            vector_stats = self.vector_store.get_stats()
        
        # Count unique documents from vector metadata if documents list is empty
        unique_docs = set()
        if self.vector_store.metadata:
            for metadata in self.vector_store.metadata:
                if 'title' in metadata:
                    unique_docs.add(metadata['title'])
        
        # Use in-memory count if available, otherwise count from vectors
        doc_count = len(self.documents) if self.documents else len(unique_docs)
        
        return {
            'documents_count': doc_count,
            'chunks_count': vector_stats['total_vectors'],
            'vectors_ready': vector_stats['total_vectors'] > 0,
            'ready_for_questions': vector_stats['total_vectors'] > 0,
            'embedding_dimension': vector_stats['dimension'],
            'memory_usage_mb': vector_stats['memory_usage_mb']
        }
    
    def clear_documents(self):
        """Clear all stored documents"""
        self.documents = []
        self.vector_store.clear()
        self.vector_store.save()  # Save cleared state
        print("🗑️  Cleared all documents and vectors")