import asyncio
import logging
import re
from typing import Any

import httpx

from app.azure_auth import get_foundry_auth_headers
from app.config import settings

logger = logging.getLogger(__name__)

MAX_SCOPE_CHARS = 160
MAX_MEMORY_CONTEXT_CHARS = 4000
MAX_UPDATE_TEXT_CHARS = 8000


class FoundryMemoryService:
    def __init__(self) -> None:
        self.endpoint = (settings.FOUNDRY_PROJECT_ENDPOINT or "").rstrip("/")
        self.store_name = settings.MEMORY_STORE_NAME
        self.api_version = settings.MEMORY_STORE_API_VERSION
        self.enabled = bool(self.endpoint)
        self._store_ready = False
        self._store_lock = asyncio.Lock()

    async def search_context(self, scope: str | None, prompt: str) -> str:
        if not self.enabled or not scope:
            return ""

        try:
            await self._ensure_store()
            payload = {
                "scope": self._normalize_scope(scope),
                "items": [self._message_item("user", prompt)],
                "options": {"max_memories": settings.MEMORY_STORE_MAX_MEMORIES},
            }
            response = await self._request(
                "POST",
                f"/memory_stores/{self.store_name}:search_memories",
                payload,
            )
            memories = self._extract_memories(response)
            if not memories:
                return ""

            context = "\n".join(f"- {memory}" for memory in memories)
            return (
                "Relevant long-term user memories from Microsoft Foundry. "
                "Use only when helpful and do not claim the user said something in this chat:\n"
                f"{context[:MAX_MEMORY_CONTEXT_CHARS]}"
            )
        except Exception as exc:
            logger.warning("Foundry memory search skipped after %s: %s", type(exc).__name__, exc)
            return ""

    async def update_from_turn(
        self,
        scope: str | None,
        prompt: str,
        answer: str,
    ) -> None:
        if not self.enabled or not scope:
            return

        try:
            await self._ensure_store()
            payload = {
                "scope": self._normalize_scope(scope),
                "items": [
                    self._message_item("user", prompt[:MAX_UPDATE_TEXT_CHARS]),
                    self._message_item("assistant", answer[:MAX_UPDATE_TEXT_CHARS]),
                ],
                "update_delay": 0,
            }
            await self._request(
                "POST",
                f"/memory_stores/{self.store_name}:update_memories",
                payload,
            )
        except Exception as exc:
            logger.warning("Foundry memory update skipped after %s: %s", type(exc).__name__, exc)

    async def delete_scope(self, scope: str | None) -> bool:
        if not self.enabled or not scope:
            return False

        await self._ensure_store()
        await self._request(
            "POST",
            f"/memory_stores/{self.store_name}:delete_scope",
            {"scope": self._normalize_scope(scope)},
        )
        return True

    async def status(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "store": self.store_name}

        try:
            await self._ensure_store()
            return {"enabled": True, "ready": True, "store": self.store_name}
        except Exception as exc:
            logger.warning("Foundry memory status unavailable after %s: %s", type(exc).__name__, exc)
            return {
                "enabled": True,
                "ready": False,
                "store": self.store_name,
                "detail": str(exc),
            }

    async def _ensure_store(self) -> None:
        if self._store_ready:
            return

        async with self._store_lock:
            if self._store_ready:
                return

            try:
                await self._request("GET", f"/memory_stores/{self.store_name}")
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
                await self._request(
                    "POST",
                    "/memory_stores",
                    {
                        "name": self.store_name,
                        "description": "Long-term user memory for the MS Tech Demo router",
                        "definition": {
                            "kind": "default",
                            "chat_model": settings.MEMORY_STORE_CHAT_MODEL,
                            "embedding_model": settings.MEMORY_STORE_EMBEDDING_MODEL,
                            "options": {
                                "chat_summary_enabled": True,
                                "user_profile_enabled": True,
                                "user_profile_details": (
                                    "Remember architecture preferences, preferred response style, "
                                    "technology choices, and recurring demo context. Avoid credentials, "
                                    "financial data, precise location, and other sensitive personal data."
                                ),
                            },
                        },
                    },
                )

            self._store_ready = True

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = await asyncio.to_thread(get_foundry_auth_headers)
        headers["Content-Type"] = "application/json"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"{self.endpoint}{path}",
                params={"api-version": self.api_version},
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    def _normalize_scope(self, scope: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_.:@-]", "-", scope.strip())
        if not normalized:
            raise ValueError("Memory scope is empty")
        return normalized[:MAX_SCOPE_CHARS]

    def _message_item(self, role: str, text: str) -> dict[str, Any]:
        return {
            "type": "message",
            "role": role,
            "content": [{"type": "input_text", "text": text}],
        }

    def _extract_memories(self, response: dict[str, Any]) -> list[str]:
        values = []
        for memory in response.get("memories", []):
            item = memory.get("memory_item", memory)
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                values.append(content.strip())
        return values


_memory_service = FoundryMemoryService()


def get_memory_service() -> FoundryMemoryService:
    return _memory_service
