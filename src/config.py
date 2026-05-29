from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AssistantConfig:
    assistant_name: str = "Atenea"
    language: str = "es-ES"
    listen_timeout: int = 7
    phrase_time_limit: int = 12
    voice_rate: int = 165
    voice_volume: float = 1.0
    memory_path: Path = Path(os.getenv("ASSISTANT_MEMORY_PATH", ".assistant_memory/memory.json"))
    ai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.2")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    gemini_fallback_models: tuple[str, ...] = tuple(
        model.strip()
        for model in os.getenv(
            "GEMINI_FALLBACK_MODELS",
            "gemini-2.5-flash,gemini-3-flash-preview,gemini-2.0-flash",
        ).split(",")
        if model.strip()
    )
    ai_provider_order: tuple[str, ...] = tuple(
        provider.strip().lower()
        for provider in os.getenv("AI_PROVIDERS", "openai,gemini").split(",")
        if provider.strip()
    )
    ai_enabled: bool = bool(os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY"))
