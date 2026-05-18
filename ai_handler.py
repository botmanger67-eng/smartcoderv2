import asyncio
import json
import logging
from typing import Optional, Dict, List, Any

import httpx
from config import (
    DEEPSEEK_API_KEY, 
    DEEPSEEK_BASE_URL, 
    DEEPSEEK_MODEL,
    DEEPSEEK_MAX_TOKENS,
    DEEPSEEK_TEMPERATURE
)

logger = logging.getLogger(__name__)


class AIHandler:
    """
    Handles communication with DeepSeek API.
    Maintains conversation history and adapts responses based on user mode.
    Fixed: Proper API URL, better error handling, full context support.
    """

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        # ✅ FIXED: Ensure /v1 is in the URL
        base = DEEPSEEK_BASE_URL or "https://api.deepseek.com"
        self.base_url = base.rstrip('/') + "/v1"
        self.model = DEEPSEEK_MODEL or "deepseek-chat"
        self.max_tokens = DEEPSEEK_MAX_TOKENS or 4096
        self.temperature = DEEPSEEK_TEMPERATURE or 0.7
        self.timeout = 60.0
        self._http_client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"AI Handler initialized: {self.model} @ {self.base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Create or return existing async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
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
            self._http_client = None

    async def get_response(
        self, 
        user_id: int, 
        chat_id: int, 
        message: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        Get AI response for a given user message.

        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            message: User message text
            context: Optional context dict with mode, history, etc.

        Returns:
            AI response text
        """
        try:
            from database import get_conversation_history, save_message, get_user

            # Fetch conversation history
            history = await asyncio.to_thread(get_conversation_history, user_id)
            
            # Get user mode
            mode = "chat"
            if context and hasattr(context, 'user_data'):
                mode = context.user_data.get("mode", "chat")

            # Build system prompt
            system_prompt = self._build_system_prompt(mode, user_id)

            # Build messages array
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add last 20 messages for context
            for msg in history[-20:]:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            
            # Add current message
            messages.append({"role": "user", "content": message})

            # Call DeepSeek API
            response_text = await self._call_api(messages)

            # Save messages to database
            await asyncio.to_thread(save_message, user_id, "user", message)
            await asyncio.to_thread(save_message, user_id, "assistant", response_text)

            return response_text

        except Exception as e:
            logger.error(f"AIHandler error for user {user_id}: {e}", exc_info=True)
            return "😔 Sorry, main abhi response generate nahi kar pa raha. Kripya thodi der baad try karein."

    def _build_system_prompt(self, mode: str, user_id: int) -> str:
        """
        Build system prompt based on user mode.

        Args:
            mode: User mode ('chat', 'project', 'code')
            user_id: User ID

        Returns:
            System prompt string
        """
        base_prompt = (
            "You are SmartBot, a friendly multimodal AI assistant on Telegram. "
            "You can chat, help with code, create projects, and analyze images/voice. "
            "Respond in the user's language (Hinglish, Urdu, English, Hindi). "
            "Be helpful, concise, and warm. "
            "You have memory of past conversations with this user."
        )

        if mode == "project":
            base_prompt += (
                "\n\n⚠️ PROJECT MODE ACTIVE: "
                "The user wants to create a project. "
                "Help them define requirements, suggest file structure, "
                "and generate code. Ask clarifying questions if needed."
            )
        elif mode == "code":
            base_prompt += (
                "\n\n💻 CODE MODE ACTIVE: "
                "The user wants direct code. "
                "Provide clean, working code with brief explanations. "
                "Use proper formatting and best practices."
            )

        return base_prompt

    async def _call_api(self, messages: List[Dict[str, str]]) -> str:
        """
        Call DeepSeek chat completion API.

        Args:
            messages: List of message dictionaries with role and content

        Returns:
            Response text from the model

        Raises:
            httpx.HTTPError: On API errors
        """
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            
            if "choices" not in data or len(data["choices"]) == 0:
                logger.error(f"Unexpected API response: {data}")
                return "API se unexpected response mila."
                
            return data["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            if e.response.status_code == 401:
                return "🔑 API key galat hai. Please admin se contact karein."
            elif e.response.status_code == 429:
                return "⏰ Rate limit reached. Thodi der wait karein."
            elif e.response.status_code == 500:
                return "🖥️ DeepSeek server error. Baad mein try karein."
            elif e.response.status_code == 503:
                return "🔧 DeepSeek under maintenance. Jald wapas aayega."
            else:
                return f"❌ API error {e.response.status_code}. Baad mein try karein."

        except httpx.TimeoutException:
            logger.error("Request timeout")
            return "⏰ Request timeout ho gaya. Dobara try karein."

        except Exception as e:
            logger.error(f"API call failed: {e}", exc_info=True)
            raise

    async def transcribe_audio(self, audio_bytes: bytes) -> Optional[str]:
        """
        Transcribe audio using DeepSeek (if supported).
        Currently returns placeholder - future implementation.
        
        Args:
            audio_bytes: Audio file bytes

        Returns:
            Transcribed text or None
        """
        # TODO: Implement when DeepSeek adds audio endpoint
        logger.info("Audio transcription requested (not yet implemented)")
        return None

    async def analyze_image(self, image_bytes: bytes) -> Optional[str]:
        """
        Analyze image using DeepSeek Vision (if supported).
        Currently returns placeholder - future implementation.

        Args:
            image_bytes: Image file bytes

        Returns:
            Image description or None
        """
        # TODO: Implement when DeepSeek adds vision endpoint
        logger.info("Image analysis requested (not yet implemented)")
        return "🖼️ Image received! (Image analysis coming soon)"

    async def clear_conversation(self, user_id: int) -> bool:
        """
        Clear conversation history for a user.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        try:
            from database import clear_user_history
            await asyncio.to_thread(clear_user_history, user_id)
            return True
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return False
