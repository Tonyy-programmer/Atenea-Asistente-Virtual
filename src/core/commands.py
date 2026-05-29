from dataclasses import dataclass
from datetime import datetime
import unicodedata

from src.core.actions import SystemActions
from src.core.ai_intent import AIIntentResolver


@dataclass(frozen=True)
class CommandResult:
    message: str
    should_stop: bool = False
    ai_used: str = ""
    mode_used: str = "sin usar"


class CommandRouter:
    def __init__(
        self,
        actions: SystemActions | None = None,
        ai_resolver: AIIntentResolver | None = None,
    ) -> None:
        self.actions = actions or SystemActions()
        self.ai_resolver = ai_resolver
        self.last_action_context: dict[str, str] | None = None
        self.pending_context_action: dict[str, str] | None = None

    def handle(self, text: str) -> CommandResult:
        command = self._normalize_command(text)

        if command == "error de conexion":
            return CommandResult("No pude conectar con el servicio de reconocimiento de voz.")

        if self._contains_any(command, ("salir", "terminar", "adios", "adios atenea")):
            return CommandResult("Hasta luego. Fue un gusto ayudarte.", should_stop=True)

        if command == "cancelar contexto":
            self.last_action_context = None
            self.pending_context_action = None
            return CommandResult("Contexto cancelado. Ya no actuare sobre la ventana anterior.", mode_used="predeterminado")

        if command in ("confirmar", "confirma", "si confirma", "si confirmo"):
            return self._execute_pending_context_action()

        if self._requests_command_mode(command):
            command = self._remove_command_mode_instruction(command)
            contextual_result = self._handle_contextual_command(command)
            if contextual_result:
                return contextual_result

            local_result = self._handle_with_local_commands(command)
            if local_result:
                return local_result

            return CommandResult("No pude resolverlo con comandos predeterminados.", mode_used="predeterminado")

        if self.last_action_context:
            contextual_ai_result = self._handle_contextual_with_ai(command, self.last_action_context["target"])
            if contextual_ai_result:
                return contextual_ai_result

        ai_result = self._handle_with_ai(command)
        if ai_result:
            return ai_result

        click_result = self._handle_click_command(command)
        if click_result:
            return click_result

        contextual_result = self._handle_contextual_command(command)
        if contextual_result:
            return contextual_result

        local_result = self._handle_with_local_commands(command)

        if self.ai_resolver and self.ai_resolver.last_error:
            if local_result:
                return CommandResult(
                    message=f"{self.ai_resolver.last_error} Use el modo predeterminado. {local_result.message}",
                    should_stop=local_result.should_stop,
                    ai_used=self.ai_resolver.last_provider or "sin IA disponible",
                    mode_used="predeterminado",
                )

            return CommandResult(
                message=f"{self.ai_resolver.last_error} No pude resolverlo con el modo predeterminado.",
                ai_used=self.ai_resolver.last_provider or "sin IA disponible",
                mode_used="sin usar",
            )

        if local_result:
            return local_result

        return CommandResult("Todavia no tengo ese comando registrado.", mode_used="sin usar")

    def _handle_with_local_commands(self, command: str) -> CommandResult | None:
        if self._contains_any(command, ("hola", "buenas", "buenos dias", "buenas tardes")):
            return CommandResult("Hola. Dime que necesitas.", mode_used="predeterminado")

        if "hora" in command:
            now = datetime.now().strftime("%H:%M")
            return CommandResult(f"Son las {now}.", mode_used="predeterminado")

        if "fecha" in command:
            today = datetime.now().strftime("%d/%m/%Y")
            return CommandResult(f"Hoy es {today}.", mode_used="predeterminado")

        app_name = self._extract_target(command, ("abre", "abrir", "inicia", "iniciar", "ejecuta", "ejecutar"))
        if app_name and self.actions.open_app(app_name):
            return self._opened_context_result("app", app_name, f"Abriendo {app_name}.")

        if app_name and self.actions.open_installed_app(app_name):
            return self._opened_context_result("app", app_name, f"Abriendo {app_name}.")

        website_name = self._extract_target(command, ("abre pagina", "abrir pagina", "abre web", "abrir web"))
        if website_name and self.actions.open_website(website_name):
            return self._opened_context_result("web", website_name, f"Abriendo {website_name}.")

        if app_name and self.actions.open_website(app_name):
            return self._opened_context_result("web", app_name, f"Abriendo {app_name}.")

        folder_name = self._extract_target(command, ("abre carpeta", "abrir carpeta"))
        if folder_name and self.actions.open_folder(folder_name):
            return self._opened_context_result("carpeta", folder_name, f"Abriendo la carpeta {folder_name}.")

        search_query = self._extract_target(command, ("busca", "buscar", "busca en google", "buscar en google"))
        if search_query and self.actions.search_google(search_query):
            return CommandResult(f"Buscando {search_query} en Google.", mode_used="predeterminado")

        mentioned_app = self.actions.find_app_mentioned_in_text(command)
        if mentioned_app and self.actions.open_installed_app(mentioned_app):
            return self._opened_context_result("app", mentioned_app, f"Abriendo {mentioned_app}.")

        return None

    def _handle_with_ai(self, command: str) -> CommandResult | None:
        if not self.ai_resolver:
            return None

        intent = self.ai_resolver.resolve(command)

        if not intent:
            return None

        if intent.action == "open_app":
            if self.actions.open_app(intent.target) or self.actions.open_installed_app(intent.target):
                return self._opened_context_result(
                    "app",
                    intent.target,
                    intent.message or f"Abriendo {intent.target}.",
                    ai_used=self.ai_resolver.last_provider if self.ai_resolver else "",
                    mode_used="memoria" if self.ai_resolver and self.ai_resolver.last_provider == "memoria local" else "IA",
                )
            return self._ai_result(f"La IA entendio que quieres abrir {intent.target}, pero no encontre esa app.")

        if intent.action == "open_website":
            if self.actions.open_website(intent.target):
                return self._opened_context_result(
                    "web",
                    intent.target,
                    intent.message or f"Abriendo {intent.target}.",
                    ai_used=self.ai_resolver.last_provider if self.ai_resolver else "",
                    mode_used="memoria" if self.ai_resolver and self.ai_resolver.last_provider == "memoria local" else "IA",
                )
            if self.actions.search_google(intent.target):
                return self._ai_result("No tengo ese sitio registrado. Lo busque en Google.")

        if intent.action == "open_folder":
            if self.actions.open_folder(intent.target):
                return self._opened_context_result(
                    "carpeta",
                    intent.target,
                    intent.message or f"Abriendo la carpeta {intent.target}.",
                    ai_used=self.ai_resolver.last_provider if self.ai_resolver else "",
                    mode_used="memoria" if self.ai_resolver and self.ai_resolver.last_provider == "memoria local" else "IA",
                )
            return self._ai_result(f"La IA entendio que quieres abrir {intent.target}, pero no encontre esa carpeta.")

        if intent.action == "search_google":
            if self.actions.search_google(intent.target):
                return self._ai_result(intent.message or f"Buscando {intent.target} en Google.")

        if intent.action == "type_text":
            target = self._current_context_target()
            text_to_type = self._remove_send_instruction(intent.target)

            if text_to_type and self.actions.type_text(text_to_type):
                if self._contains_send_instruction(command) and self.actions.press_key("enter"):
                    return self._context_ai_result(f"Escribiendo y enviando en {target}.")

                return self._context_ai_result(f"Escribiendo en {target}. Quieres que lo mande?")

        if intent.action == "send_message":
            target = self._current_context_target()

            if self.actions.press_key("enter"):
                return self._context_ai_result(f"Enviando en {target}.")

        if intent.action == "press_key":
            target = self._current_context_target()
            allowed_keys = {"enter", "tab", "backspace", "esc", "escape"}
            key = intent.target.lower().strip()

            if key in allowed_keys and self.actions.press_key(key):
                return self._context_ai_result(f"Ejecutando {key} en {target}.")

        if intent.action == "hotkey":
            target = self._current_context_target()
            allowed_hotkeys = {
                "ctrl+c": ("ctrl", "c"),
                "ctrl+v": ("ctrl", "v"),
                "ctrl+a": ("ctrl", "a"),
            }
            hotkey = intent.target.lower().replace(" ", "")

            if hotkey in allowed_hotkeys and self.actions.hotkey(allowed_hotkeys[hotkey]):
                return self._context_ai_result(f"Ejecutando accion en {target}.")

        if intent.action == "click_current":
            target = self._current_context_target()
            self.pending_context_action = {"action": "click", "target": target}
            return self._context_ai_result(
                f"Voy a hacer clic en la posicion actual del mouse para {target}. Di confirmar para continuar."
            )

        if intent.action == "answer":
            return self._ai_result(intent.message or intent.target)

        return None

    def _ai_result(self, message: str) -> CommandResult:
        ai_used = self.ai_resolver.last_provider if self.ai_resolver else ""
        mode = "memoria" if ai_used == "memoria local" else "IA"
        return CommandResult(message, ai_used=ai_used, mode_used=mode)

    def _opened_context_result(
        self,
        context_type: str,
        target: str,
        message: str,
        ai_used: str = "",
        mode_used: str = "predeterminado",
    ) -> CommandResult:
        self.last_action_context = {"type": context_type, "target": target}
        return CommandResult(
            f"{message} Necesitas que haga algo mas en esta ventana?",
            ai_used=ai_used,
            mode_used=mode_used,
        )

    def _handle_contextual_command(self, command: str) -> CommandResult | None:
        if not self.last_action_context:
            return None

        target = self.last_action_context["target"]

        text_to_type = self._extract_text_to_type(command)

        if text_to_type:
            should_send = self._contains_send_instruction(text_to_type)
            cleaned_text = self._remove_send_instruction(text_to_type)

            if cleaned_text:
                validation_message = self._validate_context_window(target)

                if validation_message:
                    self.pending_context_action = {
                        "action": "type_send" if should_send else "type",
                        "target": target,
                        "text": cleaned_text,
                    }
                    return CommandResult(
                        f"{validation_message} Di confirmar para escribir en {target}.",
                        mode_used="contexto",
                    )

                if self.actions.type_text(cleaned_text):
                    if should_send and self.actions.press_key("enter"):
                        return CommandResult(
                            f"Escribiendo y enviando en {target}.",
                            mode_used="contexto",
                        )

                    return CommandResult(
                        f"Escribiendo en {target}. Quieres que lo mande?",
                        mode_used="contexto",
                    )

        if self._contains_send_instruction(command) and self.actions.press_key("enter"):
            return CommandResult(
                f"Enviando en {target}.",
                mode_used="contexto",
            )

        key_commands = {
            "presiona enter": "enter",
            "presionar enter": "enter",
            "enter": "enter",
            "presiona tab": "tab",
            "presionar tab": "tab",
            "tab": "tab",
            "borra": "backspace",
            "borrar": "backspace",
        }

        if command in key_commands and self.actions.press_key(key_commands[command]):
            return CommandResult(f"Ejecutando {key_commands[command]} en {target}.", mode_used="contexto")

        hotkey_commands = {
            "copia": ("ctrl", "c"),
            "copiar": ("ctrl", "c"),
            "pega": ("ctrl", "v"),
            "pegar": ("ctrl", "v"),
            "selecciona todo": ("ctrl", "a"),
            "seleccionar todo": ("ctrl", "a"),
        }

        if command in hotkey_commands and self.actions.hotkey(hotkey_commands[command]):
            return CommandResult(f"Ejecutando accion en {target}.", mode_used="contexto")

        return None

    def _handle_click_command(self, command: str) -> CommandResult | None:
        if not self._is_click_here_instruction(command):
            return None

        target = self._current_context_target()
        self.pending_context_action = {"action": "click", "target": target}
        return CommandResult(
            f"Voy a hacer clic en la posicion actual del mouse para {target}. Di confirmar para continuar.",
            mode_used="contexto",
        )

    def _execute_pending_context_action(self) -> CommandResult:
        if not self.pending_context_action:
            return CommandResult("No hay ninguna accion pendiente para confirmar.", mode_used="contexto")

        action = self.pending_context_action
        self.pending_context_action = None
        target = action["target"]

        if action["action"] == "click" and self.actions.click_current_position():
            return CommandResult(f"Hice clic en la posicion actual del mouse para {target}.", mode_used="contexto")

        if action["action"] in {"type", "type_send"} and self.actions.type_text(action["text"]):
            if action["action"] == "type_send" and self.actions.press_key("enter"):
                return CommandResult(f"Escribiendo y enviando en {target}.", mode_used="contexto")

            return CommandResult(f"Escribiendo en {target}. Quieres que lo mande?", mode_used="contexto")

        return CommandResult("No pude ejecutar la accion pendiente.", mode_used="contexto")

    def _validate_context_window(self, target: str) -> str:
        active_title = self.actions.get_active_window_title()

        if not active_title:
            return ""

        normalized_target = target.lower()
        normalized_title = active_title.lower()

        if normalized_target in normalized_title or normalized_title in normalized_target:
            return ""

        return f"El contexto es {target}, pero la ventana activa parece ser {active_title}."

    def _current_context_target(self) -> str:
        if self.last_action_context:
            return self.last_action_context["target"]

        active_title = self.actions.get_active_window_title()
        return active_title or "la ventana actual"

    def _handle_contextual_with_ai(self, command: str, target: str) -> CommandResult | None:
        if not self.ai_resolver:
            return None

        intent = self.ai_resolver.resolve_contextual(command, target)

        if not intent:
            return None

        if intent.action == "type_text":
            text_to_type = self._remove_send_instruction(intent.target)

            if text_to_type and self.actions.type_text(text_to_type):
                if self._contains_send_instruction(command) and self.actions.press_key("enter"):
                    return self._context_ai_result(f"Escribiendo y enviando en {target}.")

                return self._context_ai_result(f"Escribiendo en {target}. Quieres que lo mande?")

        if intent.action == "send_message":
            if self.actions.press_key("enter"):
                return self._context_ai_result(f"Enviando en {target}.")

        if intent.action == "press_key":
            allowed_keys = {"enter", "tab", "backspace", "esc", "escape"}
            key = intent.target.lower().strip()

            if key in allowed_keys and self.actions.press_key(key):
                return self._context_ai_result(f"Ejecutando {key} en {target}.")

        if intent.action == "hotkey":
            allowed_hotkeys = {
                "ctrl+c": ("ctrl", "c"),
                "ctrl+v": ("ctrl", "v"),
                "ctrl+a": ("ctrl", "a"),
            }
            hotkey = intent.target.lower().replace(" ", "")

            if hotkey in allowed_hotkeys and self.actions.hotkey(allowed_hotkeys[hotkey]):
                return self._context_ai_result(f"Ejecutando accion en {target}.")

        if intent.action == "click_current":
            self.pending_context_action = {"action": "click", "target": target}
            return self._context_ai_result(
                f"Voy a hacer clic en la posicion actual del mouse para {target}. Di confirmar para continuar."
            )

        return None

    def _context_ai_result(self, message: str) -> CommandResult:
        ai_used = self.ai_resolver.last_provider if self.ai_resolver else ""
        return CommandResult(message, ai_used=ai_used, mode_used="IA contexto")

    @staticmethod
    def _contains_any(text: str, options: tuple[str, ...]) -> bool:
        return any(option in text for option in options)

    @staticmethod
    def _extract_target(text: str, prefixes: tuple[str, ...]) -> str:
        for prefix in sorted(prefixes, key=len, reverse=True):
            if text.startswith(prefix):
                return text.replace(prefix, "", 1).strip()

        return ""

    @staticmethod
    def _extract_text_to_type(text: str) -> str:
        for prefix in ("escribe", "escribir", "dicta", "dictar", "pon", "poner"):
            if text.startswith(prefix):
                return text.replace(prefix, "", 1).strip()

        return ""

    @staticmethod
    def _contains_send_instruction(text: str) -> bool:
        send_phrases = (
            "envia",
            "env?a",
            "enviar",
            "envia mensaje",
            "env?a mensaje",
            "enviar mensaje",
            "manda",
            "mandar",
            "mandalo",
            "mandalo ya",
            "y envia",
            "y enviar",
            "y manda",
            "y mandalo",
        )
        return any(phrase in text for phrase in send_phrases)

    @staticmethod
    def _is_click_here_instruction(text: str) -> bool:
        if ("click" in text or "clic" in text) and ("aqui" in text or "aqu?" in text or "aca" in text):
            return True

        click_phrases = (
            "haz clic aqui",
            "has clic aqui",
            "clic aqui",
            "click aqui",
            "da clic aqui",
            "da click aqui",
            "dale clic aqui",
            "dale click aqui",
        )
        return any(phrase in text for phrase in click_phrases)

    @staticmethod
    def _remove_send_instruction(text: str) -> str:
        cleaned_text = text

        for phrase in (
            "y envialo",
            "y envia",
            "y env?a",
            "y enviar",
            "y mandalo",
            "y manda",
            "envia mensaje",
            "env?a mensaje",
            "enviar mensaje",
            "mandalo ya",
            "mandalo",
            "envia",
            "env?a",
            "enviar",
            "manda",
            "mandar",
        ):
            cleaned_text = cleaned_text.replace(phrase, "")

        return " ".join(cleaned_text.split())

    @staticmethod
    def _normalize_command(text: str) -> str:
        normalized = unicodedata.normalize("NFD", text.lower().strip())
        without_accents = "".join(character for character in normalized if unicodedata.category(character) != "Mn")
        return " ".join(without_accents.split())

    @staticmethod
    def _requests_command_mode(text: str) -> bool:
        command_mode_phrases = (
            "usa comandos",
            "usar comandos",
            "utiliza comandos",
            "utilizar comandos",
            "modo comandos",
            "con comandos",
            "sin ia",
        )
        return any(phrase in text for phrase in command_mode_phrases)

    @staticmethod
    def _remove_command_mode_instruction(text: str) -> str:
        cleaned_text = text

        for phrase in (
            "usa comandos",
            "usar comandos",
            "utiliza comandos",
            "utilizar comandos",
            "modo comandos",
            "con comandos",
            "sin ia",
        ):
            cleaned_text = cleaned_text.replace(phrase, "")

        return " ".join(cleaned_text.split())
