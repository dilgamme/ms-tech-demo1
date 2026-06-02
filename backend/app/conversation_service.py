import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.azure_auth import get_foundry_auth_headers
from app.config import settings

logger = logging.getLogger(__name__)

MAX_TITLE_CHARS = 72
MAX_MESSAGE_CHARS = 12000


class FoundryConversationService:
    def __init__(self) -> None:
        self.endpoint = (settings.FOUNDRY_PROJECT_ENDPOINT or "").rstrip("/")
        self.enabled = bool(self.endpoint and settings.FOUNDRY_CONVERSATIONS_ENABLED)

    async def list_conversations(self, owner_scope: str) -> list[dict[str, Any]]:
        self._require_enabled()
        response = await self._request("GET", "/openai/v1/conversations", params={"limit": 100, "order": "desc"})
        conversations = []
        for conversation in response.get("data", []):
            metadata = conversation.get("metadata") or {}
            if metadata.get("owner_scope") != owner_scope:
                continue
            conversations.append(self._summary(conversation))
        return conversations

    async def create_conversation(self, owner_scope: str, title: str | None = None) -> dict[str, Any]:
        self._require_enabled()
        now = self._timestamp()
        response = await self._request(
            "POST",
            "/openai/v1/conversations",
            {
                "metadata": {
                    "owner_scope": owner_scope,
                    "title": self._title(title),
                    "updated_at": now,
                }
            },
        )
        return self._summary(response)

    async def get_conversation(self, owner_scope: str, conversation_id: str) -> dict[str, Any]:
        conversation = await self._owned_conversation(owner_scope, conversation_id)
        items = await self._request("GET", f"/openai/v1/conversations/{conversation_id}/items", params={"limit": 100})
        return {
            **self._summary(conversation),
            "messages": self._messages(items.get("data", [])),
        }

    async def delete_conversation(self, owner_scope: str, conversation_id: str) -> None:
        await self._owned_conversation(owner_scope, conversation_id)
        await self._request("DELETE", f"/openai/v1/conversations/{conversation_id}")

    async def append_turn(
        self,
        owner_scope: str,
        conversation_id: str | None,
        prompt: str,
        answer: str,
        model_used: str,
        reason: str,
    ) -> str | None:
        if not self.enabled:
            return conversation_id

        try:
            if conversation_id:
                conversation = await self._owned_conversation(owner_scope, conversation_id)
            else:
                conversation = await self.create_conversation(owner_scope, prompt)
                conversation_id = conversation["id"]

            await self._request(
                "POST",
                f"/openai/v1/conversations/{conversation_id}/items",
                {
                    "items": [
                        self._message_item("user", prompt),
                        self._message_item("assistant", answer, model_used, reason),
                    ]
                },
            )
            metadata = conversation.get("metadata") or {}
            await self._request(
                "POST",
                f"/openai/v1/conversations/{conversation_id}",
                {
                    "metadata": {
                        **metadata,
                        "owner_scope": owner_scope,
                        "title": self._title(metadata.get("title") or prompt),
                        "updated_at": self._timestamp(),
                    }
                },
            )
            return conversation_id
        except Exception as exc:
            logger.warning("Foundry conversation persistence skipped after %s: %s", type(exc).__name__, exc)
            return conversation_id

    async def _owned_conversation(self, owner_scope: str, conversation_id: str) -> dict[str, Any]:
        conversation = await self._request("GET", f"/openai/v1/conversations/{conversation_id}")
        if (conversation.get("metadata") or {}).get("owner_scope") != owner_scope:
            raise PermissionError("Conversation does not belong to this user")
        return conversation

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = await asyncio.to_thread(get_foundry_auth_headers)
        headers["Content-Type"] = "application/json"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"{self.endpoint}{path}",
                headers=headers,
                json=payload,
                params=params,
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise RuntimeError("Foundry conversations are not configured")

    def _summary(self, conversation: dict[str, Any]) -> dict[str, Any]:
        metadata = conversation.get("metadata") or {}
        return {
            "id": conversation["id"],
            "title": metadata.get("title") or "New conversation",
            "createdAt": conversation.get("created_at"),
            "updatedAt": metadata.get("updated_at") or conversation.get("created_at"),
            "metadata": metadata,
        }

    def _messages(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        messages = []
        for item in reversed(items):
            role = item.get("role")
            if role not in {"user", "assistant"}:
                continue
            text = self._content_text(item.get("content"))
            if not text:
                continue
            metadata = item.get("metadata") or {}
            messages.append({
                "id": item.get("id"),
                "role": role,
                "content": text,
                "modelUsed": metadata.get("model_used"),
                "reason": metadata.get("reason"),
            })
        return messages

    def _message_item(
        self,
        role: str,
        text: str,
        model_used: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "type": "message",
            "role": role,
            "content": [{"type": "input_text", "text": text[:MAX_MESSAGE_CHARS]}],
        }
        if role == "assistant":
            item["metadata"] = {
                "model_used": (model_used or "")[:512],
                "reason": (reason or "")[:512],
            }
        return item

    def _content_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and part.get("text")
            )
        return ""

    def _title(self, value: str | None) -> str:
        title = " ".join((value or "New conversation").strip().split())
        return title[:MAX_TITLE_CHARS] or "New conversation"

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()


_conversation_service = FoundryConversationService()


def get_conversation_service() -> FoundryConversationService:
    return _conversation_service
