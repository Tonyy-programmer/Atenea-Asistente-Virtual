from src.assistant import VirtualAssistant
from src.config import AssistantConfig
from src.core.actions import SystemActions
from src.core.ai_intent import AIIntentResolver
from src.core.commands import CommandRouter
from src.core.memory import AssistantMemory
from src.speech.listener import MicrophoneListener
from src.speech.speaker import VoiceSpeaker
from src.ui.desktop_app import AssistantDesktopApp


def build_assistant() -> VirtualAssistant:
    config = AssistantConfig()
    actions = SystemActions()
    memory = AssistantMemory(config.memory_path)
    ai_resolver = (
        AIIntentResolver(
            openai_model=config.ai_model,
            gemini_model=config.gemini_model,
            gemini_fallback_models=config.gemini_fallback_models,
            provider_order=config.ai_provider_order,
            actions=actions,
            memory=memory,
        )
        if config.ai_enabled
        else None
    )
    speaker = VoiceSpeaker(rate=config.voice_rate, volume=config.voice_volume)
    listener = MicrophoneListener(
        language=config.language,
        timeout=config.listen_timeout,
        phrase_time_limit=config.phrase_time_limit,
    )
    router = CommandRouter(actions=actions, ai_resolver=ai_resolver)

    return VirtualAssistant(
        name=config.assistant_name,
        listener=listener,
        speaker=speaker,
        router=router,
    )


def main() -> None:
    app = build_desktop_app()
    app.run()


def main_console() -> None:
    assistant = build_assistant()
    assistant.run()


def build_desktop_app() -> AssistantDesktopApp:
    config = AssistantConfig()
    actions = SystemActions()
    memory = AssistantMemory(config.memory_path)
    ai_resolver = (
        AIIntentResolver(
            openai_model=config.ai_model,
            gemini_model=config.gemini_model,
            gemini_fallback_models=config.gemini_fallback_models,
            provider_order=config.ai_provider_order,
            actions=actions,
            memory=memory,
        )
        if config.ai_enabled
        else None
    )
    speaker = VoiceSpeaker(rate=config.voice_rate, volume=config.voice_volume)
    listener = MicrophoneListener(
        language=config.language,
        timeout=config.listen_timeout,
        phrase_time_limit=config.phrase_time_limit,
    )
    router = CommandRouter(actions=actions, ai_resolver=ai_resolver)

    return AssistantDesktopApp(
        assistant_name=config.assistant_name,
        listener=listener,
        speaker=speaker,
        router=router,
    )
