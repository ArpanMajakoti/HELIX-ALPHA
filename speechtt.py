import json
import os
import re
import urllib.request
import wave
import zipfile
from pathlib import Path


VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
MODEL_DIR = Path("models")
MODEL_NAME = "vosk-model-en-us-0.22"
CHUNK_FRAMES = 8000


class SpeechToText:
    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or str(MODEL_DIR / MODEL_NAME)
        self._ensure_model()
        self._load_vosk()
        print("[STT] ✅ Speech recognition ready")

    def _ensure_model(self):
        target = Path(self.model_path)
        marker = target / "am" if target.exists() else None
        if marker and marker.exists():
            return
        print("[STT] Vosk model not found — downloading (~50 MB)...")
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = MODEL_DIR / "_vosk_download.zip"
        try:
            def _progress(block, block_size, total):
                if total > 0:
                    pct = min(100, block * block_size * 100 // total)
                    print(f"\r[STT] Downloading... {pct}%", end="", flush=True)
            urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path, _progress)
            print()
            print("[STT] Extracting model...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(MODEL_DIR)
            zip_path.unlink(missing_ok=True)
            print(f"[STT] Model ready at {self.model_path}")
        except Exception as exc:
            if zip_path.exists():
                zip_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Failed to download Vosk model: {exc}\n"
                f"Manual download: {VOSK_MODEL_URL}\n"
                f"Extract to: {self.model_path}"
            ) from exc

    def _load_vosk(self):
        try:
            from vosk import Model, KaldiRecognizer
            self._model = Model(self.model_path)
            self._Recognizer = KaldiRecognizer
        except ImportError as exc:
            raise ImportError(
                "Vosk not installed. Run: pip install vosk"
            ) from exc

    def _build_recognizer(self, frame_rate: int):
        rec = self._Recognizer(self._model, float(frame_rate))
        rec.SetWords(True)
        rec.SetPartialWords(False)
        return rec

    def _clean_text(self, text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def transcribe(self, audio_path: str) -> str:
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            wf = wave.open(audio_path, "rb")
        except wave.Error as exc:
            raise ValueError(f"Corrupt WAV file: {exc}") from exc

        if wf.getnchannels() != 1:
            wf.close()
            raise ValueError("Audio must be mono (1 channel).")
        if wf.getsampwidth() != 2:
            wf.close()
            raise ValueError("Audio must be 16-bit PCM.")

        rec = self._build_recognizer(wf.getframerate())
        parts: list[str] = []

        while True:
            data = wf.readframes(CHUNK_FRAMES)
            if not data:
                break
            if rec.AcceptWaveform(data):
                res = json.loads(rec.Result())
                word = res.get("text", "").strip()
                if word:
                    parts.append(word)

        final = json.loads(rec.FinalResult())
        tail = final.get("text", "").strip()
        if tail:
            parts.append(tail)

        wf.close()

        full = self._clean_text(" ".join(parts))
        if full:
            print(f'[STT] 📝 "{full}"')
        else:
            print("[STT] ⚠  No speech detected.")
        return full
