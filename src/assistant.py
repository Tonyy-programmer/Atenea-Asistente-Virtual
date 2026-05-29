from src.core.commands import CommandRouter
from src.speech.listener import MicrophoneListener
from src.speech.speaker import VoiceSpeaker


class VirtualAssistant:
    def __init__(
        self,
        name: str,
        listener: MicrophoneListener,
        speaker: VoiceSpeaker,
        router: CommandRouter,
    ) -> None:
        self.name = name
        self.listener = listener
        self.speaker = speaker
        self.router = router

    def run(self) -> None:
        self.speaker.say(f"Hola, soy {self.name}. Estoy lista para escucharte.")

        while True:
            text = self.listener.listen()

            if not text:
                self.speaker.say("No entendi la peticion. Intentalo otra vez.")
                continue

            print(f"Usuario: {text}")
            result = self.router.handle(text)
            if result.ai_used:
                print(f"IA utilizada: {result.ai_used}")
            print(f"Modo utilizado: {result.mode_used}")
            self.speaker.say(result.message)

            if result.should_stop:
                break
