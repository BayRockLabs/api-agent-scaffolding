"""
LLM service with OAuth token management.
This is CORE INFRASTRUCTURE - Do not modify.
"""

import httpx
from typing import AsyncIterator, Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import json
import structlog

from app.core.config import settings
from app.core.exceptions import LLMException

logger = structlog.get_logger()


class LLMService:
    """
    LLM service with OAuth authentication and token management.
    Supports both streaming and non-streaming responses.
    """
    
    def __init__(self):
        self.api_url = settings.LLM_API_URL
        self.oauth_url = settings.LLM_OAUTH_TOKEN_URL
        self.client_id = settings.LLM_CLIENT_ID
        self.client_secret = settings.LLM_CLIENT_SECRET
        self.model = settings.LLM_MODEL
        
        # Token management
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._token_lock = asyncio.Lock()
    
    async def _get_access_token(self) -> str:
        """
        Get or refresh OAuth access token.
        Thread-safe with automatic refresh.
        """
        # Check if token is still valid
        if self.access_token and self.token_expiry:
            if datetime.utcnow() < self.token_expiry:
                return self.access_token
        
        # Acquire lock for token refresh
        async with self._token_lock:
            # Double-check after acquiring lock
            if self.access_token and self.token_expiry:
                if datetime.utcnow() < self.token_expiry:
                    return self.access_token
            
            # Refresh token
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.oauth_url,
                        data={
                            "grant_type": "client_credentials",
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                        },
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    self.access_token = data["access_token"]
                    
                    # Set expiry with 60 second buffer
                    expires_in = data.get("expires_in", 3600)
                    self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                    
                    logger.info(
                        "OAuth token refreshed",
                        expires_in=expires_in,
                        expiry=self.token_expiry.isoformat(),
                    )
                    
                    return self.access_token
                    
            except httpx.HTTPError as e:
                logger.error("OAuth token refresh failed", error=str(e))
                raise LLMException(
                    f"Failed to get OAuth token: {str(e)}",
                    details={"oauth_url": self.oauth_url}
                )
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Non-streaming chat completion.
        
        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            temperature: Model temperature (default from settings)
            max_tokens: Maximum tokens (default from settings)
            stream: Enable streaming (should be False for this method)
            **kwargs: Additional model parameters
            
        Returns:
            Dict with completion response
            
        Raises:
            LLMException: If API call fails
        """
        if stream:
            raise ValueError("Use chat_completion_stream() for streaming responses")
        
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "stream": False,
            **kwargs
        }
        
        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
                logger.info(
                    "LLM request",
                    model=self.model,
                    messages_count=len(messages),
                    temperature=payload["temperature"],
                )
                
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                
                result = response.json()
                
                logger.info(
                    "LLM response received",
                    finish_reason=result.get("choices", [{}])[0].get("finish_reason"),
                )
                
                return result
                
        except httpx.HTTPError as e:
            logger.error(
                "LLM API request failed",
                error=str(e),
                status_code=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
            )
            raise LLMException(
                f"LLM request failed: {str(e)}",
                details={"model": self.model, "error": str(e)}
            )
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Streaming chat completion.
        
        Args:
            messages: List of message dicts
            temperature: Model temperature
            max_tokens: Maximum tokens
            **kwargs: Additional model parameters
            
        Yields:
            String chunks from the model
            
        Raises:
            LLMException: If streaming fails
        """
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
            "stream": True,
            **kwargs
        }
        
        try:
            async with httpx.AsyncClient(timeout=settings.STREAM_TIMEOUT) as client:
                logger.info(
                    "LLM streaming request",
                    model=self.model,
                    messages_count=len(messages),
                )
                
                async with client.stream(
                    "POST",
                    self.api_url,
                    json=payload,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            
                            if data == "[DONE]":
                                logger.info("LLM streaming completed")
                                break
                            
                            try:
                                chunk = json.loads(data)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                                
                                if content:
                                    yield content
                                    
                            except json.JSONDecodeError:
                                logger.warning("Failed to parse streaming chunk", data=data)
                                continue
                                
        except httpx.HTTPError as e:
            logger.error("LLM streaming failed", error=str(e))
            raise LLMException(
                f"LLM streaming failed: {str(e)}",
                details={"model": self.model}
            )
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get text embedding (if supported by LLM provider).
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        # Implementation depends on your LLM provider's embedding API
        # This is a placeholder
        raise NotImplementedError("Embedding support not implemented")


# Global instance
llm_service = LLMService()
