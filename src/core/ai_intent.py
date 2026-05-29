import json
import os

from google import genai
from google.genai import types
from openai import OpenAI

from src.core.actions import SystemActions
from src.core.intent import AssistantIntent
from src.core.memory import AssistantMemory


class AIIntentResolver:
    def __init__(
        self,
        openai_model: str,
        gemini_model: str,
        gemini_fallback_models: tuple[str, ...],
        provider_order: tuple[str, ...],
        actions: SystemActions,
        memory: AssistantMemory,
    ) -> None:
        self.openai_model = openai_model
        self.gemini_model = gemini_model
        self.gemini_models = self._unique_models((gemini_model, *gemini_fallback_models))
        self.provider_order = provider_order
        self.actions = actions
        self.memory = memory
        self.last_error = ""
        self.last_provider = ""
        self.openai_client = OpenAI() if os.getenv("OPENAI_API_KEY") else None
        self.gemini_client = genai.Client() if os.getenv("GEMINI_API_KEY") else None

    def resolve(self, user_text: str) -> AssistantIntent | None:
        self.last_error = ""
        self.last_provider = ""

        cached_intent = self.memory.get_intent(user_text)
        if cached_intent:
            self.last_provider = "memoria local"
            return cached_intent

        for provider in self.provider_order:
            intent = self._resolve_with_provider(provider, user_text)

            if intent:
                self.memory.remember_intent(user_text, intent, self.last_provider)
                return intent

        return None

    def resolve_contextual(self, user_text: str, context_target: str) -> AssistantIntent | None:
        self.last_error = ""
        self.last_provider = ""
        contextual_text = (
            f"Contexto activo: {context_target}. "
            f"Interpreta esta orden como accion dentro de esa ventana: {user_text}"
        )

        for provider in self.provider_order:
            intent = self._resolve_with_provider(provider, contextual_text)

            if intent:
                return intent

        return None

    def _resolve_with_provider(self, provider: str, user_text: str) -> AssistantIntent | None:
        if provider == "openai" and self.openai_client:
            return self._resolve_with_openai(user_text)

        if provider == "gemini" and self.gemini_client:
            return self._resolve_with_gemini(user_text)

        return None

    def _resolve_with_openai(self, user_text: str) -> AssistantIntent | None:
        try:
            response = self.openai_client.responses.create(
                model=self.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": self._system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": user_text,
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "assistant_intent",
                        "strict": True,
                        "schema": self._openai_intent_schema(),
                    }
                },
            )
            payload = json.loads(response.output_text)
            self.last_provider = f"OpenAI {self.openai_model}"
            return AssistantIntent(
                action=payload["action"],
                target=payload["target"].lower().strip(),
                message=payload["message"].strip(),
            )
        except Exception as error:
            self._remember_error("OpenAI", error)
            return None

    def _resolve_with_gemini(self, user_text: str) -> AssistantIntent | None:
        for model in self.gemini_models:
            try:
                response = self.gemini_client.models.generate_content(
                    model=model,
                    contents=f"{self._system_prompt()}\n\nPeticion del usuario: {user_text}",
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=self._gemini_intent_schema(),
                    ),
                )
                payload = json.loads(response.text)
                self.last_provider = f"Gemini {model}"
                return AssistantIntent(
                    action=payload["action"],
                    target=payload["target"].lower().strip(),
                    message=payload["message"].strip(),
                )
            except Exception as error:
                self._remember_error(f"Gemini {model}", error)

        return None

    def _remember_error(self, provider: str, error: Exception) -> None:
        error_text = str(error)
        print(f"Error usando {provider}: {error_text}")

        if "RESOURCE_EXHAUSTED" in error_text or "insufficient_quota" in error_text:
            self.last_error = f"{provider} no funciona ahora porque no tiene cuota disponible."
            return

        if "UNAVAILABLE" in error_text or "high demand" in error_text:
            self.last_error = f"{provider} no funciona ahora porque esta temporalmente saturada."
            return

        self.last_error = f"{provider} esta configurada, pero fallo al interpretar la peticion."

    @staticmethod
    def _unique_models(models: tuple[str, ...]) -> tuple[str, ...]:
        unique_models = []

        for model in models:
            if model and model not in unique_models:
                unique_models.append(model)

        return tuple(unique_models)

    def _openai_intent_schema(self) -> dict:
        schema = self._base_intent_schema()
        schema["additionalProperties"] = False
        return schema

    def _gemini_intent_schema(self) -> dict:
        return self._base_intent_schema()

    def _base_intent_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "open_app",
                        "open_website",
                        "open_folder",
                        "search_google",
                        "type_text",
                        "send_message",
                        "press_key",
                        "hotkey",
                        "click_current",
                        "answer",
                        "unknown",
                    ],
                },
                "target": {
                    "type": "string",
                    "description": "Aplicacion, sitio, carpeta, busqueda o respuesta corta.",
                },
                "message": {
                    "type": "string",
                    "description": "Mensaje breve para decirle al usuario.",
                },
            },
            "required": ["action", "target", "message"],
        }

    def _system_prompt(self) -> str:
        apps = ", ".join(sorted(self.actions.installed_apps.keys())[:120])
        websites = ", ".join(sorted(self.actions.websites.keys()))
        folders = ", ".join(sorted(self.actions.folders.keys()))

        return (
            "Eres el interprete de intenciones de un asistente virtual de Windows. "
            "No ejecutes acciones, solo clasifica la peticion del usuario. "
            "Usa open_app cuando quiera abrir una aplicacion, open_website para sitios web, "
            "open_folder para carpetas, search_google para busquedas, answer para preguntas simples "
            "y unknown cuando no sea claro. "
            "Si hay contexto activo de una ventana, puedes usar type_text para escribir texto, "
            "send_message para enviar o presionar enter, press_key para una tecla simple y hotkey "
            "para combinaciones como ctrl+c, ctrl+v o ctrl+a. Usa click_current cuando el usuario "
            "pida hacer clic aqui, ahi, en esto, o sobre la posicion actual del mouse. "
            "Para type_text, target debe ser exactamente el texto a escribir. "
            "Para press_key, target debe ser una tecla como enter, tab o backspace. "
            "Para hotkey, target debe usar teclas separadas por +, por ejemplo ctrl+v. "
            "El usuario habla por voz y la transcripcion puede tener errores, palabras sin acento "
            "o palabras parecidas; interpreta la intencion de forma flexible. "
            "No propongas acciones peligrosas como borrar archivos, modificar seguridad, instalar software "
            "o ejecutar comandos arbitrarios. "
            f"Aplicaciones detectadas: {apps}. "
            f"Sitios conocidos: {websites}. "
            f"Carpetas conocidas: {folders}. "
            "Responde siempre en espanol."
        )
