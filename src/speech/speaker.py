import pyttsx3


class VoiceSpeaker:
    def __init__(self, rate: int, volume: float) -> None:
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", volume)

    def say(self, text: str) -> None:
        print(f"Asistente: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
