"""
Retrieval-Augmented Generation (RAG) module for document retrieval and context building.
"""
import os
from typing import List, Tuple
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from config import settings


class RAGSystem:
    """Handles document retrieval and embedding operations."""
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
        
        self.search_client = SearchClient(
            endpoint=f"https://{settings.azure_search_service_name}.search.windows.net/",
            index_name=settings.azure_search_index_name,
            credential=AzureKeyCredential(settings.azure_search_api_key)
        )
        
        self.embedding_deployment = settings.azure_openai_embedding_deployment
    
    def get_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text using Azure OpenAI."""
        response = self.client.embeddings.create(
            input=text,
            model=self.embedding_deployment
        )
        return response.data[0].embedding
    
    def retrieve_relevant_documents(self, query: str, top_k: int = 5) -> Tuple[List[str], List[str]]:
        """
        Retrieve relevant documents from Azure Search based on query.
        
        Args:
            query: User query
            top_k: Number of documents to retrieve
            
        Returns:
            Tuple of (documents, sources)
        """
        try:
            # Get embeddings for the query
            query_embedding = self.get_embeddings(query)
            
            # Search in Azure Search using vector search
            results = self.search_client.search(
                search_text=query,
                vector_queries=[query_embedding],
                top=top_k,
                select=["content", "source", "doc_id"]
            )
            
            documents = []
            sources = []
            
            for result in results:
                documents.append(result["content"])
                sources.append(result.get("source", result.get("doc_id", "unknown")))
            
            return documents, sources
        
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return [], []
    
    def build_context(self, documents: List[str]) -> str:
        """Build context string from retrieved documents."""
        if not documents:
            return ""
        
        context = "\n---\n".join(documents)
        return f"Context from documents:\n{context}"


class SessionMemory:
    """Manages conversation history per session."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages = []
    
    def add_message(self, role: str, content: str):
        """Add a message to the session history."""
        self.messages.append({
            "role": role,
            "content": content
        })
    
    def get_messages(self) -> List[dict]:
        """Get all messages in the session."""
        return self.messages
    
    def clear(self):
        """Clear session history."""
        self.messages = []


# Global session storage (in production, use Redis/database)
SESSIONS = {}

def get_or_create_session(session_id: str) -> SessionMemory:
    """Get or create a session."""
    if session_id not in SESSIONS:
        SESSIONS[session_id] = SessionMemory(session_id)
    return SESSIONS[session_id]
