from __future__ import annotations

import json
import os
import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError


@dataclass(frozen=True)
class ConversationStoreSettings:
    host: str
    port: int
    db: int
    password: str
    ttl_seconds: int
    max_messages: int
    key_prefix: str = "ihrs:consult:conversation:"
    user_conversation_key_prefix: str = "ihrs:consult:user-conversation:"

    @classmethod
    def from_env(cls) -> "ConversationStoreSettings":
        return cls(
            host=os.getenv("REDIS_HOST", "localhost").strip(),
            port=int(os.getenv("REDIS_PORT", "6379").strip()),
            db=int(os.getenv("REDIS_DB", "0").strip()),
            password=os.getenv("REDIS_PASSWORD", "").strip(),
            ttl_seconds=int(os.getenv("CONSULT_CONTEXT_TTL_SECONDS", "43200").strip()),
            max_messages=int(os.getenv("CONSULT_CONTEXT_MAX_MESSAGES", "12").strip()),
        )


class ConversationStore:
    def __init__(self, settings: ConversationStoreSettings | None = None) -> None:
        self.settings = settings or ConversationStoreSettings.from_env()
        self._client = Redis(
            host=self.settings.host,
            port=self.settings.port,
            db=self.settings.db,
            password=self.settings.password or None,
            decode_responses=True,
        )

    def new_conversation_id(self) -> str:
        return uuid.uuid4().hex

    async def start_new_conversation_for_user(self, user_key: str | None, conversation_id: str) -> None:
        normalized_user_key = self._normalize_user_key(user_key)
        if not normalized_user_key or not conversation_id:
            return

        mapping_key = self._user_conversation_key(normalized_user_key)

        try:
            previous_conversation_id = await self._client.get(mapping_key)
            if previous_conversation_id and previous_conversation_id != conversation_id:
                await self._client.delete(self._key(previous_conversation_id))

            await self._client.set(mapping_key, conversation_id, ex=self.settings.ttl_seconds)
        except RedisError:
            return

    async def bind_user_conversation(self, user_key: str | None, conversation_id: str | None) -> None:
        normalized_user_key = self._normalize_user_key(user_key)
        normalized_conversation_id = str(conversation_id or "").strip()
        if not normalized_user_key or not normalized_conversation_id:
            return

        try:
            await self._client.set(
                self._user_conversation_key(normalized_user_key),
                normalized_conversation_id,
                ex=self.settings.ttl_seconds,
            )
        except RedisError:
            return

    async def get_user_conversation_id(self, user_key: str | None) -> str | None:
        normalized_user_key = self._normalize_user_key(user_key)
        if not normalized_user_key:
            return None

        mapping_key = self._user_conversation_key(normalized_user_key)
        try:
            conversation_id = await self._client.get(mapping_key)
            if not conversation_id:
                return None
            exists = await self._client.exists(self._key(conversation_id))
            if not exists:
                await self._client.delete(mapping_key)
                return None
            await self._client.expire(mapping_key, self.settings.ttl_seconds)
            return str(conversation_id).strip() or None
        except RedisError:
            return None

    async def get_history(self, conversation_id: str | None) -> list[dict[str, str]]:
        if not conversation_id:
            return []

        try:
            payload = await self._client.get(self._key(conversation_id))
        except RedisError:
            return []

        if not payload:
            return []

        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return []

        if not isinstance(data, list):
            return []

        history: list[dict[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip()
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                history.append({"role": role, "content": content})

        if history:
            try:
                await self._client.expire(self._key(conversation_id), self.settings.ttl_seconds)
            except RedisError:
                return history

        return history

    async def append_messages(self, conversation_id: str, messages: list[dict[str, Any]]) -> None:
        if not conversation_id or not messages:
            return

        existing = await self.get_history(conversation_id)
        normalized_new_messages: list[dict[str, str]] = []
        for item in messages:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip()
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                normalized_new_messages.append({"role": role, "content": content})

        if not normalized_new_messages:
            return

        merged = (existing + normalized_new_messages)[-self.settings.max_messages :]
        try:
            await self._client.set(
                self._key(conversation_id),
                json.dumps(merged, ensure_ascii=False),
                ex=self.settings.ttl_seconds,
            )
        except RedisError:
            return

    async def delete_conversation(self, conversation_id: str | None) -> None:
        if not conversation_id:
            return

        try:
            await self._client.delete(self._key(conversation_id))
        except RedisError:
            return

    async def clear_user_conversation_if_matches(self, user_key: str | None, conversation_id: str | None) -> None:
        normalized_user_key = self._normalize_user_key(user_key)
        normalized_conversation_id = str(conversation_id or "").strip()
        if not normalized_user_key or not normalized_conversation_id:
            return

        mapping_key = self._user_conversation_key(normalized_user_key)
        try:
            current_conversation_id = await self._client.get(mapping_key)
            if current_conversation_id == normalized_conversation_id:
                await self._client.delete(mapping_key)
        except RedisError:
            return

    def _key(self, conversation_id: str) -> str:
        return f"{self.settings.key_prefix}{conversation_id}"

    def _user_conversation_key(self, user_key: str) -> str:
        return f"{self.settings.user_conversation_key_prefix}{user_key}"

    def _normalize_user_key(self, user_key: str | None) -> str:
        normalized = str(user_key or "").strip()
        if not normalized:
            return ""
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
