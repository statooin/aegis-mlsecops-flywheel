"""
Aegis AI Gateway - Guard Service Package.

Этот пакет реализует архитектуру каскадных фильтров (L1 Heuristics -> L2 ML Semantic)
для защиты LLM-инфраструктуры от Prompt Injection и социальной инженерии.
"""

__version__ = "2.0.0"

from .config import settings, logger
from .main import app

__all__ = ["app", "settings", "logger"]