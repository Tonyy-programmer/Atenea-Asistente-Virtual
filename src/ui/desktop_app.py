import threading
import time
import tkinter as tk
import winsound
from tkinter import ttk

from src.core.commands import CommandRouter
from src.speech.listener import MicrophoneListener
from src.speech.speaker import VoiceSpeaker


class AssistantDesktopApp:
    def __init__(
        self,
        assistant_name: str,
        listener: MicrophoneListener,
        speaker: VoiceSpeaker,
        router: CommandRouter,
    ) -> None:
        self.assistant_name = assistant_name
        self.listener = listener
        self.speaker = speaker
        self.router = router
        self.is_listening = False
        self.is_processing = False
        self.background_enabled = True
        self.background_listening_enabled = False
        self.listen_lock = threading.Lock()
        self.speech_lock = threading.Lock()

        self.root = tk.Tk()
        self.root.title(f"{self.assistant_name} - Asistente virtual")
        self.root.geometry("680x640")
        self.root.minsize(560, 600)
        self.root.configure(bg="#0b1020")

        self.status_var = tk.StringVar(value="Lista para escuchar")
        self.user_text_var = tk.StringVar(value="Tu peticion aparecera aqui")
        self.answer_var = tk.StringVar(value=f"Hola, soy {self.assistant_name}.")
        self.ai_used_var = tk.StringVar(value="IA: sin usar")
        self.mode_used_var = tk.StringVar(value="Modo: sin usar")

        self._build_styles()
        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_background)

    def run(self) -> None:
        self.root.after(350, self._welcome)
        self.root.after(900, self._start_background_listener)
        self.root.mainloop()

    def _build_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Main.TFrame", background="#0b1020")
        style.configure("Header.TFrame", background="#0b1020")
        style.configure("Panel.TFrame", background="#131b2e")
        style.configure("StatusBar.TFrame", background="#0f766e")
        style.configure("Title.TLabel", background="#0b1020", foreground="#f8fafc", font=("Segoe UI", 28, "bold"))
        style.configure("Subtitle.TLabel", background="#0b1020", foreground="#b6c2d6", font=("Segoe UI", 11))
        style.configure("Status.TLabel", background="#0b1020", foreground="#67e8f9", font=("Segoe UI", 12, "bold"))
        style.configure("StatusBar.TLabel", background="#0f766e", foreground="#ecfeff", font=("Segoe UI", 10, "bold"))
        style.configure("PanelTitle.TLabel", background="#131b2e", foreground="#7dd3fc", font=("Segoe UI", 10, "bold"))
        style.configure("PanelText.TLabel", background="#131b2e", foreground="#f8fafc", font=("Segoe UI", 14))
        style.configure("Meta.TLabel", background="#131b2e", foreground="#aeb9ca", font=("Segoe UI", 10))
        style.configure("Listen.TButton", font=("Segoe UI", 15, "bold"), padding=(24, 16))
        style.map(
            "Listen.TButton",
            background=[("active", "#38bdf8"), ("disabled", "#475569"), ("!disabled", "#0ea5e9")],
            foreground=[("disabled", "#cbd5e1"), ("!disabled", "#ffffff")],
        )
        style.configure("Exit.TButton", font=("Segoe UI", 10), padding=(14, 10), background="#263244", foreground="#e2e8f0")
        style.map("Exit.TButton", background=[("active", "#334155")])

    def _build_layout(self) -> None:
        status_bar = ttk.Frame(self.root, style="StatusBar.TFrame", padding=(12, 7))
        status_bar.pack(fill="x")
        ttk.Label(
            status_bar,
            text="X = segundo plano  |  Salir = cerrar aplicacion",
            style="StatusBar.TLabel",
        ).pack(anchor="center")

        main = ttk.Frame(self.root, style="Main.TFrame", padding=28)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main, style="Header.TFrame")
        header.pack(fill="x")

        title = ttk.Label(header, text=self.assistant_name, style="Title.TLabel")
        title.pack(anchor="center")

        subtitle = ttk.Label(header, text="Asistente inteligente con voz, IA y automatizacion", style="Subtitle.TLabel")
        subtitle.pack(anchor="center", pady=(2, 12))

        status = ttk.Label(header, textvariable=self.status_var, style="Status.TLabel")
        status.pack(anchor="center")

        self.visualizer = tk.Canvas(
            main,
            width=210,
            height=190,
            bg="#0b1020",
            highlightthickness=0,
            bd=0,
        )
        self.visualizer.pack(pady=(20, 20))
        self._draw_visualizer(is_active=False)

        user_card = ttk.Frame(main, style="Panel.TFrame", padding=18)
        user_card.pack(fill="x", pady=(0, 14))

        ttk.Label(user_card, text="Escuche", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(
            user_card,
            textvariable=self.user_text_var,
            style="PanelText.TLabel",
            wraplength=560,
        ).pack(anchor="w", pady=(8, 0))

        answer_card = ttk.Frame(main, style="Panel.TFrame", padding=18)
        answer_card.pack(fill="both", expand=True, pady=(0, 18))

        ttk.Label(answer_card, text="Respuesta", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(
            answer_card,
            textvariable=self.answer_var,
            style="PanelText.TLabel",
            wraplength=560,
        ).pack(anchor="w", pady=(8, 0))
        ttk.Label(
            answer_card,
            textvariable=self.ai_used_var,
            style="Meta.TLabel",
            wraplength=560,
        ).pack(anchor="w", pady=(12, 0))
        ttk.Label(
            answer_card,
            textvariable=self.mode_used_var,
            style="Meta.TLabel",
            wraplength=560,
        ).pack(anchor="w", pady=(4, 0))

        controls = ttk.Frame(main, style="Main.TFrame")
        controls.pack(fill="x")

        self.listen_button = ttk.Button(
            controls,
            text="Hablar",
            style="Listen.TButton",
            command=self._start_listening,
        )
        self.listen_button.pack(side="left", fill="x", expand=True)

        ttk.Button(
            controls,
            text="Salir",
            style="Exit.TButton",
            command=self._exit_app,
        ).pack(side="left", padx=(12, 0))

    def _draw_visualizer(self, is_active: bool) -> None:
        self.visualizer.delete("all")

        if is_active:
            outer_color = "#38bdf8"
            middle_color = "#14b8a6"
            center_color = "#f8fafc"
            text_color = "#111827"
            label = "ON"
        else:
            outer_color = "#334155"
            middle_color = "#1e293b"
            center_color = "#0f172a"
            text_color = "#94a3b8"
            label = "MIC"

        self.visualizer.create_oval(16, 4, 194, 182, outline=outer_color, width=3)
        self.visualizer.create_oval(38, 26, 172, 160, outline=middle_color, width=12)
        self.visualizer.create_oval(70, 58, 140, 128, fill=center_color, outline="#475569", width=1)
        self.visualizer.create_line(105, 75, 105, 110, fill=text_color, width=6, capstyle="round")
        self.visualizer.create_arc(89, 94, 121, 128, start=180, extent=180, outline=text_color, width=4)
        self.visualizer.create_line(105, 128, 105, 138, fill=text_color, width=3)
        self.visualizer.create_line(95, 138, 115, 138, fill=text_color, width=3)
        self.visualizer.create_text(105, 166, text=label, fill="#cbd5e1", font=("Segoe UI", 10, "bold"))

    def _welcome(self) -> None:
        self._speak(f"Hola, soy {self.assistant_name}. Estoy lista para escucharte.")

    def _start_background_listener(self) -> None:
        worker = threading.Thread(target=self._background_listen_loop, daemon=True)
        worker.start()

    def _background_listen_loop(self) -> None:
        while self.background_enabled:
            if not self.background_listening_enabled or self.is_listening or self.is_processing:
                time.sleep(0.2)
                continue

            self.is_listening = True
            self.root.after(0, lambda: self.status_var.set("Esperando activacion..."))
            wake_text = self._listen_once(timeout=2, phrase_time_limit=3)
            self.is_listening = False

            wake_text = self._normalize_text(wake_text)

            if not wake_text:
                continue

            if self._is_exit_request(wake_text):
                self.root.after(0, self._exit_app)
                return

            if self._is_show_window_request(wake_text):
                self.root.after(0, self._show_window)
                continue

            if self._contains_wake_word(wake_text):
                request = self._extract_request_after_wake_word(wake_text)
            else:
                request = wake_text

            if not request:
                self.is_processing = True
                self.root.after(0, lambda: self.status_var.set("Activada. Esperando peticion..."))
                self._speak("Que necesitas?")
                self.is_processing = False

                self.is_listening = True
                self.root.after(0, lambda: self.status_var.set("Escuchando peticion..."))
                self._beep_listening()
                request = self._listen_once(timeout=7, phrase_time_limit=12)
                self.is_listening = False

            if request:
                self._process_recognized_text(request)
            else:
                self._beep_not_understood()

    def _start_listening(self) -> None:
        if self.is_listening or self.is_processing:
            return

        self.background_listening_enabled = False
        self.is_listening = True
        self.listen_button.configure(state="disabled")
        self.status_var.set("Habla ahora...")
        self.user_text_var.set("Habla ahora")
        self.answer_var.set("Procesando tu peticion...")
        self.ai_used_var.set("IA: esperando respuesta")
        self.mode_used_var.set("Modo: escuchando")
        self._draw_visualizer(is_active=True)

        worker = threading.Thread(target=self._listen_and_answer, daemon=True)
        worker.start()

    def _listen_and_answer(self) -> None:
        self._beep_listening()
        text = self._listen_once()
        self._process_recognized_text(text)

    def _process_recognized_text(self, text: str) -> None:
        self.is_processing = True
        self.root.after(0, lambda: self.status_var.set("Procesando..."))

        if not text:
            self._beep_not_understood()
            answer = "No entendi la peticion. Intentalo otra vez."
            self.root.after(
                0,
                lambda: self._update_interaction_ui(
                    user_text="No se detecto una peticion clara",
                    answer=answer,
                    ai_used="",
                    mode_used="sin usar",
                ),
            )
            self._speak(answer)
            self._finish_processing()
            return

        result = self.router.handle(text)
        if result.ai_used:
            print(f"IA utilizada: {result.ai_used}")
        print(f"Modo utilizado: {result.mode_used}")
        self.root.after(
            0,
            lambda: self._update_interaction_ui(
                user_text=text,
                answer=result.message,
                ai_used=result.ai_used,
                mode_used=result.mode_used,
            ),
        )
        self._speak(result.message)
        self._finish_processing()

        if result.should_stop:
            self.root.after(900, self._exit_app)

    def _finish_processing(self) -> None:
        self.is_listening = False
        self.is_processing = False
        self.background_listening_enabled = not bool(self.root.winfo_viewable())

    def _listen_once(self, timeout: int | None = None, phrase_time_limit: int | None = None) -> str:
        with self.listen_lock:
            return self.listener.listen(timeout=timeout, phrase_time_limit=phrase_time_limit)

    def _update_interaction_ui(self, user_text: str, answer: str, ai_used: str, mode_used: str) -> None:
        self.user_text_var.set(user_text)
        self.answer_var.set(answer)
        self.ai_used_var.set(f"IA: {ai_used}" if ai_used else "IA: sin usar")
        self.mode_used_var.set(f"Modo: {mode_used}")
        self.status_var.set("Lista para escuchar")
        self.listen_button.configure(state="normal")
        self._draw_visualizer(is_active=False)

    def _hide_to_background(self) -> None:
        self.root.withdraw()
        self.background_listening_enabled = True
        self._speak(f"{self.assistant_name} sigue escuchando en segundo plano.")

    def _show_window(self) -> None:
        self.background_listening_enabled = False
        self.root.deiconify()
        self.root.lift()
        self.status_var.set("Lista para escuchar")

    def _exit_app(self) -> None:
        self.background_enabled = False
        self.root.destroy()

    def _speak(self, text: str) -> None:
        with self.speech_lock:
            self.speaker.say(text)

    @staticmethod
    def _beep_listening() -> None:
        winsound.Beep(880, 140)

    @staticmethod
    def _beep_not_understood() -> None:
        winsound.Beep(330, 220)

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.lower().strip().split())

    @staticmethod
    def _contains_wake_word(text: str) -> bool:
        wake_words = ("hola", "atenea", "oye atenea", "hey atenea")
        return any(wake_word in text for wake_word in wake_words)

    @staticmethod
    def _extract_request_after_wake_word(text: str) -> str:
        request = text

        for wake_word in ("oye atenea", "hey atenea", "hola atenea", "atenea", "hola"):
            request = request.replace(wake_word, "", 1).strip()

        return request

    @staticmethod
    def _is_show_window_request(text: str) -> bool:
        show_requests = ("mostrar ventana", "muestra ventana", "abre ventana", "mostrar atenea", "muestra atenea")
        return any(request in text for request in show_requests)

    @staticmethod
    def _is_exit_request(text: str) -> bool:
        exit_requests = ("cerrar asistente", "apagar asistente", "salir atenea", "cerrar atenea")
        return any(request in text for request in exit_requests)
