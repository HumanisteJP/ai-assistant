"""Dependency Injection container for service singletons.

At runtime *main.py* populates this container with concrete service
instances (DatabaseService, GoogleService, etc.).  テストでは属性をモック
に差し替えることで依存を注入できる。
"""
from types import SimpleNamespace
from typing import Optional, Any


class _Container(SimpleNamespace):
    """A very light-weight attribute container.

    Attributes are added dynamically at the application bootstrap.
    Using :class:`types.SimpleNamespace` keeps the implementation
    dependency-free while still enabling *dot access* syntax.
    """

    # Services are populated by src/main.py on startup
    db_service: Optional[Any] = None
    google_service: Optional[Any] = None
    transcription_service: Optional[Any] = None
    processing_service: Optional[Any] = None
    audio_service: Optional[Any] = None


# Global, import-time singleton – *never* re-assigned, only mutated.
container = _Container()

__all__ = ["container"] 