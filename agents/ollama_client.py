"""
Ollama Client for MyAIGist Local
Provides unified interface to Ollama API for text generation and embeddings.
"""

import os
import requests
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self):
        """Initialize Ollama client with configuration from environment."""
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'qwen2.5:14b')
        self.embed_model = os.getenv('OLLAMA_EMBED_MODEL', 'nomic-embed-text')
        self.timeout = int(os.getenv('OLLAMA_TIMEOUT', '300'))  # 5 minutes default for slower hardware

        logger.info(f"🤖 Ollama client initialized: {self.host}, model={self.model}")

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        """
        Generate text completion using Ollama.

        Args:
            prompt: The prompt text
            system: Optional system message
            **kwargs: Additional parameters for Ollama (temperature, top_p, etc.)

        Returns:
            Generated text response

        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        url = f"{self.host}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }

        if system:
            payload["system"] = system

        try:
            logger.debug(f"🔄 Generating with Ollama: {self.model}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            return result.get("response", "")

        except requests.exceptions.Timeout:
            logger.error("⏱️  Ollama request timed out")
            raise Exception(f"Ollama request timed out after {self.timeout} seconds")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ollama API error: {str(e)}")
            raise Exception(f"Ollama API error: {str(e)}")

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Chat completion using Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters for Ollama

        Returns:
            Generated response text

        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        url = f"{self.host}/api/chat"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            **kwargs
        }

        try:
            logger.debug(f"🔄 Chat with Ollama: {self.model}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            message = result.get("message", {})
            return message.get("content", "")

        except requests.exceptions.Timeout:
            logger.error("⏱️  Ollama chat request timed out")
            raise Exception(f"Ollama chat request timed out after {self.timeout} seconds")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ollama chat API error: {str(e)}")
            raise Exception(f"Ollama chat API error: {str(e)}")

    def embed(self, text: str) -> List[float]:
        """
        Create embedding vector for text using Ollama.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats (768 dimensions for nomic-embed-text)

        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        url = f"{self.host}/api/embeddings"

        payload = {
            "model": self.embed_model,
            "prompt": text
        }

        try:
            logger.debug(f"🔄 Creating embedding with: {self.embed_model}")
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            embedding = result.get("embedding", [])

            if not embedding:
                raise Exception("Empty embedding returned from Ollama")

            return embedding

        except requests.exceptions.Timeout:
            logger.error("⏱️  Ollama embedding request timed out")
            raise Exception(f"Ollama embedding request timed out after {self.timeout} seconds")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ollama embedding API error: {str(e)}")
            raise Exception(f"Ollama embedding API error: {str(e)}")

    def health_check(self) -> bool:
        """
        Check if Ollama service is available.

        Returns:
            True if Ollama is healthy, False otherwise
        """
        try:
            url = f"{self.host}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            models = response.json().get("models", [])
            logger.info(f"✅ Ollama healthy, {len(models)} models available")
            return True

        except Exception as e:
            logger.error(f"❌ Ollama health check failed: {str(e)}")
            return False

    def list_models(self) -> List[str]:
        """
        List available Ollama models.

        Returns:
            List of model names
        """
        try:
            url = f"{self.host}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            logger.info(f"📋 Available models: {', '.join(model_names)}")
            return model_names

        except Exception as e:
            logger.error(f"❌ Failed to list models: {str(e)}")
            return []


def get_ollama_client() -> OllamaClient:
    """
    Factory function to get Ollama client instance.

    Returns:
        Configured OllamaClient instance
    """
    return OllamaClient()
