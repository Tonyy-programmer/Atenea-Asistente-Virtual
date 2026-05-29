from dataclasses import asdict
import json
from pathlib import Path
from time import time

from src.core.intent import AssistantIntent


class AssistantMemory:
    def __init__(self, path: Path, max_items: int = 250) -> None:
        self.path = path
        self.max_items = max_items
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def get_intent(self, text: str) -> AssistantIntent | None:
        key = self._key(text)
        item = self.data.get("intent_cache", {}).get(key)

        if not item:
            return None

        item["hits"] = item.get("hits", 0) + 1
        item["last_used_at"] = time()
        self.save()

        intent = item["intent"]
        return AssistantIntent(
            action=intent["action"],
            target=intent["target"],
            message=intent["message"],
        )

    def remember_intent(self, text: str, intent: AssistantIntent, provider: str) -> None:
        if not self._can_cache(intent):
            return

        cache = self.data.setdefault("intent_cache", {})
        cache[self._key(text)] = {
            "original_text": text,
            "intent": asdict(intent),
            "provider": provider,
            "hits": 0,
            "created_at": time(),
            "last_used_at": time(),
        }
        self._trim_cache()
        self.save()

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> dict:
        if not self.path.exists():
            return {"intent_cache": {}, "preferences": {}}

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"intent_cache": {}, "preferences": {}}

    def _trim_cache(self) -> None:
        cache = self.data.setdefault("intent_cache", {})

        if len(cache) <= self.max_items:
            return

        sorted_items = sorted(cache.items(), key=lambda item: item[1].get("last_used_at", 0))

        for key, _ in sorted_items[: len(cache) - self.max_items]:
            cache.pop(key, None)

    @staticmethod
    def _key(text: str) -> str:
        return " ".join(text.lower().strip().split())

    @staticmethod
    def _can_cache(intent: AssistantIntent) -> bool:
        return intent.action in {"open_app", "open_website", "open_folder", "search_google"}
