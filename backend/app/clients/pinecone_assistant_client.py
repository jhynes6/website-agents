from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Union

from fastapi import HTTPException

from ..config import get_settings


@dataclass(frozen=True)
class AssistantChatMessage:
    role: str
    content: str


class PineconeAssistantClient:
    """
    Thin wrapper around the Pinecone Assistant API (via pinecone-plugin-assistant).

    Docs (Python):
    - pc.assistant.list_assistants()
    - pc.assistant.describe_assistant(assistant_name=...)
    - pc.assistant.Assistant(assistant_name=...).chat(messages=[Message(...)], ...)
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._pc = None
        self._assistant_cache: Dict[str, Any] = {}

    def _pc_client(self):
        if not self.settings.pinecone_api_key:
            raise HTTPException(status_code=500, detail="PINECONE_API_KEY is not configured")
        if self._pc is None:
            from pinecone import Pinecone

            self._pc = Pinecone(api_key=self.settings.pinecone_api_key)
        return self._pc

    @staticmethod
    def _to_plugin_messages(messages: Sequence[Union[AssistantChatMessage, Dict[str, str]]]):
        try:
            from pinecone_plugins.assistant.models.chat import Message
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Pinecone Assistant plugin is not available. "
                    "Install/upgrade with: pip install --upgrade pinecone pinecone-plugin-assistant. "
                    f"(error: {e})"
                ),
            )

        out: List[Any] = []
        for m in messages:
            if isinstance(m, AssistantChatMessage):
                role = m.role
                content = m.content
            else:
                role = str(m.get("role") or "user")
                content = str(m.get("content") or "")
            content = (content or "").strip()
            if not content:
                continue
            out.append(Message(role=role, content=content))
        return out

    def list_assistants(self) -> Any:
        pc = self._pc_client()
        return pc.assistant.list_assistants()

    def describe_assistant(self, assistant_name: str) -> Any:
        pc = self._pc_client()
        return pc.assistant.describe_assistant(assistant_name=assistant_name)

    def assistant(self, assistant_name: Optional[str] = None) -> Any:
        name = (assistant_name or self.settings.pinecone_inbox_manager_assistant_name or "").strip()
        if not name:
            raise HTTPException(
                status_code=400,
                detail=(
                    "assistant_name is required (or set PINECONE_INBOX_MANAGER_ASSISTANT_NAME)."
                ),
            )
        if name in self._assistant_cache:
            return self._assistant_cache[name]

        pc = self._pc_client()
        a = pc.assistant.Assistant(assistant_name=name)
        self._assistant_cache[name] = a
        return a

    def chat(
        self,
        *,
        assistant_name: Optional[str] = None,
        messages: Sequence[Union[AssistantChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        stream: bool = False,
        json_response: bool = False,
        **kwargs: Any,
    ) -> Any:
        """
        Chat with an assistant. Returns either:
        - a response object (default), or
        - an iterator of streaming chunks (if stream=True)

        kwargs is forwarded to the underlying SDK call.
        """
        a = self.assistant(assistant_name)
        plugin_messages = self._to_plugin_messages(messages)

        call_kwargs: Dict[str, Any] = dict(kwargs)
        if model:
            call_kwargs["model"] = model
        if stream:
            call_kwargs["stream"] = True
        if json_response:
            call_kwargs["json_response"] = True

        return a.chat(messages=plugin_messages, **call_kwargs)

    def chat_text(
        self,
        *,
        assistant_name: Optional[str] = None,
        messages: Sequence[Union[AssistantChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Convenience helper for non-streaming chats that returns the assistant message text.
        """
        resp = self.chat(assistant_name=assistant_name, messages=messages, model=model, **kwargs)
        # The SDK returns a response object with `message.content` (per docs).
        try:
            return str(resp.message.content)
        except Exception:
            return str(resp)

    def stream_text(
        self,
        *,
        assistant_name: Optional[str] = None,
        messages: Sequence[Union[AssistantChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """
        Convenience helper for streaming chats. Yields delta content chunks as strings.
        """
        resp = self.chat(
            assistant_name=assistant_name,
            messages=messages,
            model=model,
            stream=True,
            **kwargs,
        )
        for data in resp:
            delta = getattr(data, "delta", None)
            if delta is not None:
                content = getattr(delta, "content", None)
                if content:
                    yield str(content)


pinecone_assistant_client = PineconeAssistantClient()


