from __future__ import annotations

from contextvars import ContextVar

_thread_id: ContextVar[str | None] = ContextVar("iris_thread_id", default=None)
_demo_user_id: ContextVar[str | None] = ContextVar("iris_demo_user_id", default=None)


def set_thread_id(value: str | None) -> object:
    return _thread_id.set(value)


def reset_thread_id(token: object) -> None:
    _thread_id.reset(token)


def get_thread_id() -> str | None:
    return _thread_id.get()


def set_demo_user_id(value: str | None) -> object:
    return _demo_user_id.set(value)


def reset_demo_user_id(token: object) -> None:
    _demo_user_id.reset(token)


def get_demo_user_id() -> str | None:
    return _demo_user_id.get()
