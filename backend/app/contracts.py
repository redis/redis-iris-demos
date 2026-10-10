from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    mode: Literal["context_surfaces", "simple_rag"] = "context_surfaces"
    thread_id: str | None = None
    demo_user_id: str | None = None
