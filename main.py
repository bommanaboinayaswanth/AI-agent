"""
FastAPI backend for AI Agent with RAG.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid
from agent import AIAgent
from config import settings

# Initialize FastAPI app
app = FastAPI(
    title="AI Agent RAG API",
    description="AI Agent with Retrieval-Augmented Generation for document Q&A",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent
agent = AIAgent()

# Request/Response Models
class AskRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class AskResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str
    used_tools: bool

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Agent RAG API"
    }

@app.post("/ask", response_model=AskResponse, tags=["Query"])
async def ask_question(request: AskRequest):
    """
    Ask a question to the AI agent.
    
    The agent will:
    1. Decide if it needs to search documents
    2. Use RAG to retrieve relevant documents if needed
    3. Return an answer with sources
    
    Args:
        query: The question to ask
        session_id: Optional session ID for conversation history (generated if not provided)
        
    Returns:
        Answer with sources and session information
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Process query through agent
        result = agent.process_query(request.query, session_id)
        
        return AskResponse(**result)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@app.get("/sessions/{session_id}", tags=["Session"])
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    from rag import SESSIONS
    
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    return {
        "session_id": session_id,
        "messages": session.get_messages()
    }

@app.delete("/sessions/{session_id}", tags=["Session"])
async def clear_session(session_id: str):
    """Clear conversation history for a session."""
    from rag import SESSIONS
    
    if session_id in SESSIONS:
        SESSIONS[session_id].clear()
        return {"message": f"Session {session_id} cleared"}
    
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/", tags=["Info"])
async def root():
    """API information."""
    return {
        "name": "AI Agent RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "ask": "/ask",
            "session": "/sessions/{session_id}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        debug=settings.debug
    )
