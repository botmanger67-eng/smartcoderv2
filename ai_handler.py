import asyncio
import json
from typing import Optional, Dict, List, Any

import httpx
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from database import get_history, save_message, clear_history, get_user_mode
from github_manager import GitHubManager
from utils import count_tokens, truncate_history

class AIHandler:
    """
    Handles communication with DeepSeek API.
    Maintains conversation history and adapts responses based on user mode.
    """

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_BASE_URL or "https://api.deepseek.com"
        self.model = DEEPSEEK_MODEL or "deepseek-chat"
        self.max_tokens = 4096
        self.timeout = 60.0
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Create or return existing async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._http_client

    async def close(self):
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def get_response(self, user_id: int, chat_id: int, message: str) -> str:
        """
        Get AI response for a given user message.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            message: User message text

        Returns:
            AI response text
        """
        try:
            # Fetch conversation history
            history = await get_history(user_id, chat_id)

            # Determine user mode
            mode = await get_user_mode(user_id)

            # Build system prompt based on mode
            system_prompt = self._build_system_prompt(mode, user_id, chat_id)

            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": message})

            # Truncate history if needed to fit token limit
            max_context_tokens = self.max_tokens - 512  # reserve for response
            messages = await truncate_history(messages, max_context_tokens, count_tokens)

            # Call DeepSeek API
            response_text = await self._call_api(messages)

            # Save messages to database
            await save_message(user_id, chat_id, "user", message)
            await save_message(user_id, chat_id, "assistant", response_text)

            return response_text

        except Exception as e:
            # Log error (implementation depends on project)
            print(f"AIHandler error: {e}")
            return "I'm sorry, I encountered an error while processing your request. Please try again later."

    def _build_system_prompt(self, mode: str, user_id: int, chat_id: int) -> str:
        """
        Build system prompt based on user mode.

        Args:
            mode: User mode (e.g., 'normal', 'project')
            user_id: User ID
            chat_id: Chat ID

        Returns:
            System prompt string
        """
        base_prompt = (
            "You are a multimodal AI assistant integrated with Telegram. "
            "You have access to the user's conversation history and can remember context. "
            "Respond helpfully and concisely."
        )

        if mode == "project":
            # Add project-specific context
            github = GitHubManager()
            repo_context = github.get_repository_context(user_id, chat_id)
            if repo_context:
                base_prompt += f"\n\nCurrent project context:\n{repo_context}"

        return base_prompt

    async def _call_api(self, messages: List[Dict[str, str]]) -> str:
        """
        Call DeepSeek chat completion API.

        Args:
            messages: List of message dictionaries with role and content

        Returns:
            Response text from the model
        """
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.7,
            "stream": False,
        }

        try:
            response = await client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            # Handle specific HTTP errors
            if e.response.status_code == 401:
                return "Invalid API key. Please check your configuration."
            elif e.response.status_code == 429:
                # Rate limit: implement retry logic if needed
                return "I'm being rate-limited. Please wait a moment and try again."
            elif e.response.status_code == 500:
                return "DeepSeek API server error. Please try again later."
            else:
                raise

        except httpx.TimeoutException:
            return "The request timed out. Please try again."

        except Exception as e:
            # Log and re-raise for outer handler
            print(f"API call failed: {e}")
            raise

    async def clear_conversation(self, user_id: int, chat_id: int) -> bool:
        """
        Clear conversation history for a user/chat.

        Args:
            user_id: User ID
            chat_id: Chat ID

        Returns:
            True if successful, False otherwise
        """
        try:
            await clear_history(user_id, chat_id)
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False