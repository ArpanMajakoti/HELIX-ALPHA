import asyncio
import os
import subprocess
import threading
from pathlib import Path


TEMP_DIR = Path("temp")
DEFAULT_VOICE = "en-GB-SoniaNeural"


class TTS:
    def __init__(self, voice: str = DEFAULT_VOICE, rate_offset: str = "+10%"):
        self.voice = voice
        self.rate_offset = rate_offset
        self._loop = None
        self._thread = None
        self._ready = False
        self._mode = "none"
        self._pyttsx_engine = None
        TEMP_DIR.mkdir(exist_ok=True)
        self._init()

    def _init(self):
        try:
            import edge_tts as _  # noqa: F401
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._loop.run_forever, daemon=True
            )
            self._thread.start()
            self._mode = "edge"
            self._ready = True
            print(f"[TTS] edge-tts ready (voice: {self.voice})")
            return
        except ImportError:
            pass

        try:
            import pyttsx3
            engine = pyttsx3.init()
            for v in engine.getProperty("voices") or []:
                if any(k in v.id.lower() for k in ("zira", "hazel", "sonia")):
                    engine.setProperty("voice", v.id)
                    break
            engine.setProperty("rate", 180)
            self._pyttsx_engine = engine
            self._mode = "pyttsx3"
            self._ready = True
            print("[TTS] pyttsx3 ready (offline)")
        except ImportError:
            print("[TTS] No TTS engine found — speech output disabled.")

    async def _edge_speak(self, text: str):
        import edge_tts
        out = str(TEMP_DIR / "tts.mp3")
        comm = edge_tts.Communicate(text, self.voice, rate=self.rate_offset)
        await comm.save(out)
        subprocess.Popen(["start", "", out], shell=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)

    def speak(self, text: str):
        if not (self._ready and text):
            return
        if self._mode == "edge":
            asyncio.run_coroutine_threadsafe(self._edge_speak(text), self._loop)
        elif self._mode == "pyttsx3":
            self._pyttsx_engine.say(text)
            self._pyttsx_engine.runAndWait()

    def shutdown(self):
        if self._loop and self._thread and self._thread.is_alive():
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=2)
