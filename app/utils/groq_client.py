"""
Groq LLM client for generating honeypot responses.

Uses Groq's ultra-fast inference API with llama-3.1-70b-versatile model.
"""
import os
import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class GroqClient:
    """
    Client for Groq LLM API with automatic backup key fallback.
    
    Groq provides ultra-fast inference (~300-500ms for responses).
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize Groq client with automatic backup key support.
        
        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
        """
        self.primary_key = api_key or os.getenv("GROQ_API_KEY")
        self.current_key = self.primary_key
        self._all_keys = [k for k in [
            self.primary_key,
            os.getenv("GROQ_BACKUP_KEY"),
            os.getenv("GROQ_BACKUP_KEY_2"),
            os.getenv("GROQ_BACKUP_KEY_3"),
            os.getenv("GROQ_BACKUP_KEY_4"),
            os.getenv("GROQ_BACKUP_KEY_5"),
            os.getenv("GROQ_BACKUP_KEY_6"),
        ] if k]  # Only include keys that are actually set in env
        
        if not self.primary_key:
            raise ValueError("Groq API key required. Set GROQ_API_KEY or pass api_key")
        
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "meta-llama/llama-4-maverick-17b-128e-instruct"
        self.timeout = 4.0
        
        logger.info(f"GroqClient initialized with {len(self._all_keys)} key(s), model: {self.model}")
    
    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 150
    ) -> str:
        """
        Generate a response using Groq LLM with automatic backup key fallback.
        
        Args:
            system_prompt: System instructions for the LLM
            user_message: User's message to respond to
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated response text
        """
        headers = {
            "Authorization": f"Bearer {self.current_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                generated_text = data["choices"][0]["message"]["content"].strip()
                logger.info(f"Groq response generated ({len(generated_text)} chars)")
                
                return generated_text
                
        except httpx.HTTPStatusError as e:
            # 429 rate limit → rotate to next available key
            if e.response.status_code == 429:
                # Find next key in rotation that isn't the current one
                try:
                    current_idx = self._all_keys.index(self.current_key)
                    next_keys = [k for i, k in enumerate(self._all_keys) if i > current_idx]
                    if next_keys:
                        self.current_key = next_keys[0]
                        logger.warning(f"Groq key rate limited, rotating to key #{current_idx + 2} of {len(self._all_keys)}")
                        return await self.generate_response(system_prompt, user_message, temperature, max_tokens)
                    else:
                        logger.error("All Groq keys rate limited")
                except ValueError:
                    pass
            logger.error(f"Groq API error: {e}")
            raise Exception(f"LLM error: {e}")
        except httpx.TimeoutException:
            logger.error("Groq API timeout")
            raise Exception("LLM timeout")
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise Exception(f"LLM error: {e}")
    
    def generate_response_sync(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.8,
        max_tokens: int = 150
    ) -> str:
        """
        Synchronous version of generate_response.
        
        Args:
            system_prompt: System instructions for the LLM
            user_message: User's message to respond to
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated response text
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                data = response.json()
                
                generated_text = data["choices"][0]["message"]["content"].strip()
                logger.info(f"Groq response generated ({len(generated_text)} chars)")
                
                return generated_text
                
        except httpx.TimeoutException:
            logger.error("Groq API timeout")
            raise Exception("LLM timeout")
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise Exception(f"LLM error: {e}")
