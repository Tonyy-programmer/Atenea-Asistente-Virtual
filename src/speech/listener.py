import speech_recognition as sr


class MicrophoneListener:
    def __init__(self, language: str, timeout: int, phrase_time_limit: int) -> None:
        self.language = language
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 250
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.4

    def listen(self, timeout: int | None = None, phrase_time_limit: int | None = None) -> str:
        try:
            listen_timeout = timeout if timeout is not None else self.timeout
            listen_phrase_time_limit = phrase_time_limit if phrase_time_limit is not None else self.phrase_time_limit

            with sr.Microphone() as source:
                print("Escuchando...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.15)
                audio = self.recognizer.listen(
                    source,
                    timeout=listen_timeout,
                    phrase_time_limit=listen_phrase_time_limit,
                )

            text = self.recognizer.recognize_google(audio, language=self.language)
            print(f"Reconocido: {text}")
            return text
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            return "error de conexion"
