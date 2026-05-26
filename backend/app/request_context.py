from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True)
class RequestContext:
    demo_user_id: str | None = None
    demo_user: dict[str, Any] | None = None


_REQUEST_CONTEXT: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


@contextmanager
def request_context_scope(*, demo_user_id: str | None = None, demo_user: dict[str, Any] | None = None) -> Iterator[None]:
    token = _REQUEST_CONTEXT.set(RequestContext(demo_user_id=demo_user_id, demo_user=demo_user))
    try:
        yield
    finally:
        _REQUEST_CONTEXT.reset(token)


def get_request_context() -> RequestContext:
    return _REQUEST_CONTEXT.get() or RequestContext()
