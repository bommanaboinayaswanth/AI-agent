"""
AI Agent module with LLM integration and tool calling.
"""
import json
from typing import Optional, Dict, Any
from openai import AzureOpenAI
from config import settings
from rag import RAGSystem, get_or_create_session


class AIAgent:
    """Main AI Agent with tool calling and LLM integration."""
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
        
        self.rag_system = RAGSystem()
        self.chat_deployment = settings.azure_openai_chat_deployment
        self.model_name = "gpt-4"
        
        # Define available tools
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "description": "Search internal documents for relevant information based on query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to find relevant documents"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of documents to retrieve",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def search_documents(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Tool function: Search documents using RAG system."""
        documents, sources = self.rag_system.retrieve_relevant_documents(query, top_k)
        
        return {
            "documents": documents,
            "sources": sources,
            "found": len(documents) > 0
        }
    
    def process_tool_call(self, tool_name: str, tool_input: Dict) -> str:
        """Process tool calls from the model."""
        if tool_name == "search_documents":
            result = self.search_documents(**tool_input)
            return json.dumps(result)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    
    def process_query(
        self,
        query: str,
        session_id: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user query with agent logic (with tool calling).
        
        Args:
            query: User query
            session_id: Session ID for memory
            system_prompt: Optional custom system prompt
            
        Returns:
            Response with answer and sources
        """
        session = get_or_create_session(session_id)
        
        # Default system prompt
        if not system_prompt:
            system_prompt = """You are a helpful AI assistant that answers questions about company internal policies and documents.
You have access to a tool called 'search_documents' that you can use to find relevant information.

When a user asks a question:
1. First, decide if you need to search documents to answer accurately
2. Use the search_documents tool if needed to find relevant information
3. Provide a clear, accurate answer based on the search results
4. Always cite your sources

Be concise and direct in your responses."""
        
        # Add user message to session
        session.add_message("user", query)
        
        # Prepare messages for API call
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(session.get_messages())
        
        # First API call with tools
        response = self.client.chat.completions.create(
            model=self.chat_deployment,
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
            max_tokens=2000,
            temperature=0.7
        )
        
        # Handle tool calls
        sources = []
        while response.choices[0].finish_reason == "tool_calls":
            # Process all tool calls
            tool_calls = response.choices[0].message.tool_calls
            
            # Add assistant response to session
            session.add_message("assistant", response.choices[0].message)
            
            # Process each tool call
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments)
                tool_result = self.process_tool_call(tool_name, tool_input)
                
                # Extract sources from document search
                if tool_name == "search_documents":
                    result_data = json.loads(tool_result)
                    sources.extend(result_data.get("sources", []))
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": tool_result
                })
                session.add_message("tool", f"{tool_name}: {tool_result}")
            
            # Second API call to get final response
            response = self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                max_tokens=2000,
                temperature=0.7
            )
        
        # Extract final answer
        final_answer = response.choices[0].message.content
        
        # Add assistant response to session
        session.add_message("assistant", final_answer)
        
        return {
            "answer": final_answer,
            "sources": list(set(sources)),  # Remove duplicates
            "session_id": session_id,
            "used_tools": True if sources else False
        }
