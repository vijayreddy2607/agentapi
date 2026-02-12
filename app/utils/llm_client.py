"""LLM client with support for Ollama and Groq (lightweight)."""
from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage
from app.config import settings
import logging
import httpx
import asyncio
import json

logger = logging.getLogger(__name__)


class OllamaLLMClient:
    """Client for Ollama local LLM."""
    
    def __init__(self):
        self.base_url = getattr(settings, 'ollama_base_url', 'http://localhost:11434')
        self.model = getattr(settings, 'ollama_model', 'llama3.1:8b')
        logger.info(f"Initialized Ollama client: {self.model} at {self.base_url}")
    
    async def ainvoke(self, messages: List[BaseMessage]) -> str:
        """Invoke Ollama API."""
        try:
            prompt = self._format_messages(messages)
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7}
                    }
                )
                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
                return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama invocation failed: {e}")
            raise

    def _format_messages(self, messages: List[BaseMessage]) -> str:
        """Convert messages to custom prompt format."""
        parts = []
        for msg in messages:
            role = "System" if isinstance(msg, SystemMessage) else "User" if isinstance(msg, HumanMessage) else "Assistant"
            parts.append(f"{role}: {msg.content}\n")
        parts.append("Assistant:")
        return "\n".join(parts)


class GroqLLMClient:
    """Lightweight Groq client using httpx with Multi-Key Rotation."""
    
    def __init__(self):
        # Initialize with multiple keys for rotation (Primary + Backup 1 + Backup 2)
        self.api_keys = [
            settings.groq_api_key,
            settings.groq_backup_key,
            settings.groq_backup_key_2,
        ]
        # Filter out duplicates and None values
        self.api_keys = list(dict.fromkeys([k for k in self.api_keys if k]))
        self.current_key_idx = 0
        
        self.base_url = settings.groq_base_url
        self.model = settings.groq_model
        logger.info(f"⚡ Groq Client initialized with {len(self.api_keys)} rotating keys")

    async def ainvoke(self, messages: List[BaseMessage]) -> str:
        """Invoke Groq API with automatic key rotation on rate limits."""
        formatted_messages = self._format_messages_json(messages)
        
        # Try each key 3 times before failing
        max_total_attempts = len(self.api_keys) * 3
        
        for attempt in range(max_total_attempts):
            current_key = self.api_keys[self.current_key_idx]
            headers = {
                "Authorization": f"Bearer {current_key}",
                "Content-Type": "application/json"
            }
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json={
                            "model": self.model,
                            "messages": formatted_messages,
                            "temperature": 0.0  # Deterministic for classification
                        }
                    )
                    
                    if response.status_code == 429:
                         raise Exception(f"Rate limit exceeded: {response.text}")
                    
                    if response.status_code != 200:
                        raise Exception(f"Groq API error: {response.status_code} - {response.text}")
                        
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                    
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    logger.warning(f"⚠️ Rate limit on Key #{self.current_key_idx + 1}. Rotating...")
                    # Rotate to next key
                    self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
                    # Short sleep before retry
                    await asyncio.sleep(1)
                else:
                    logger.error(f"❌ Groq API Error: {e}")
                    # For non-rate-limit errors, maybe retry once then fail
                    if attempt == max_total_attempts - 1:
                        raise
                        
        raise Exception("All Groq API keys exhausted (Rate Limits). Please try again later.")

    def _format_messages_json(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Format messages for Groq JSON API."""
        formatted = []
        for msg in messages:
            role = "system" if isinstance(msg, SystemMessage) else "user" if isinstance(msg, HumanMessage) else "assistant"
            formatted.append({"role": role, "content": msg.content})
        return formatted




class GeminiLLMClient:
    """Client for Google Gemini API."""
    
    def __init__(self):
        self.api_key = getattr(settings, 'google_api_key', None)
        self.model = getattr(settings, 'google_model', 'gemini-1.5-pro')
        logger.info(f"✨ Gemini Client initialized: {self.model}")
        
    async def ainvoke(self, messages: List[BaseMessage]) -> str:
        """Invoke Gemini API."""
        if not self.api_key:
            raise ValueError("Google API Key not configured")
            
        try:
            prompt = self._format_messages(messages)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.0}
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
                    
                data = response.json()
                if "candidates" in data and data["candidates"]:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                return ""
                
        except Exception as e:
            logger.error(f"Gemini invocation failed: {e}")
            raise

    def _format_messages(self, messages: List[BaseMessage]) -> str:
        """Format messages for Gemini (simple text concatenation)."""
        prompt_parts = []
        for msg in messages:
            role = "User"
            if isinstance(msg, SystemMessage):
                role = "System"
            elif isinstance(msg, AIMessage):
                role = "Model"
            prompt_parts.append(f"{role}: {msg.content}")
        return "\n\n".join(prompt_parts)


class LLMClient:
    """Universal LLM client wrapper."""
    
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        logger.info(f"Initializing LLM client with provider: {self.provider}")
        
        if self.provider == "ollama":
            self.client = OllamaLLMClient()
        elif self.provider == "groq":
            self.client = GroqLLMClient()
        elif self.provider in ["openai", "anthropic", "google", "grok"]:
            if self.provider == "google":
                self.client = GeminiLLMClient()
            
            # Fallback to heavy LangChain implementations if really needed
            elif self.provider == "openai":
                from langchain_openai import ChatOpenAI
                self.client = ChatOpenAI(model=settings.openai_model, temperature=0.7)
            elif self.provider == "grok":
                from langchain_openai import ChatOpenAI
                self.client = ChatOpenAI(
                    model=settings.grok_model, 
                    api_key=settings.grok_api_key, 
                    base_url=settings.grok_base_url
                )
            else:
                raise ValueError(f"Provider {self.provider} not fully supported in lightweight mode yet.")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    async def ainvoke(self, messages: List[BaseMessage]) -> str:
        """Invoke the underlying client."""
        if hasattr(self.client, 'ainvoke'):
            result = await self.client.ainvoke(messages)
            # LangChain returns AIMessage, our custom clients return str
            if isinstance(result, AIMessage):
                return result.content
            return result
        return str(self.client.invoke(messages).content)


# Global client instance
llm_client = LLMClient()
