import os
import time
import wave
import numpy as np
import sounddevice as sd
from pathlib import Path
from collections import deque


SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 512
SILENCE_THRESHOLD = 0.018
SILENCE_SECONDS = 1.8
PRE_ROLL_SECONDS = 0.4
MAX_SECONDS = 45.0
TEMP_DIR = Path("temp")


class AudioManager:
    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        silence_threshold: float = SILENCE_THRESHOLD,
        silence_duration: float = SILENCE_SECONDS,
        max_duration: float = MAX_SECONDS,
        pre_roll: float = PRE_ROLL_SECONDS,
    ):
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_duration = max_duration
        self.pre_roll_frames = int(pre_roll * sample_rate / CHUNK)
        TEMP_DIR.mkdir(exist_ok=True)
        self._log_device()

    def _log_device(self):
        try:
            default_idx = sd.default.device[0]
            if default_idx is not None and default_idx >= 0:
                info = sd.query_devices(default_idx)
                print(f"[Audio] Microphone: {info['name']}")
        except Exception:
            print("[Audio] Could not query microphone info.")

    def _energy(self, block: np.ndarray) -> float:
        return float(np.sqrt(np.mean(block.astype(np.float32) ** 2)))

    def _adaptive_threshold(self, noise_frames: list[np.ndarray]) -> float:
        if not noise_frames:
            return self.silence_threshold
        energies = [self._energy(f) for f in noise_frames]
        noise_floor = float(np.mean(energies))
        return max(self.silence_threshold, noise_floor * 3.5)

    def record_until_silence(self, output_path: str | None = None) -> str:
        output_path = output_path or str(TEMP_DIR / "recording.wav")

        pre_roll: deque = deque(maxlen=self.pre_roll_frames)
        captured: list[np.ndarray] = []
        silence_counter = 0
        speech_started = False
        noise_calibration: list[np.ndarray] = []
        calibration_frames = int(0.6 * self.sample_rate / CHUNK)
        threshold = self.silence_threshold
        silence_limit = int(self.silence_duration * self.sample_rate / CHUNK)
        max_frames = int(self.max_duration * self.sample_rate / CHUNK)
        frame_count = 0
        stop_flag = [False]

        def callback(indata, frames, time_info, status):
            nonlocal silence_counter, speech_started, threshold, frame_count
            if status:
                pass
            block = indata[:, 0].copy()
            energy = self._energy(block)
            frame_count += 1

            if frame_count <= calibration_frames:
                noise_calibration.append(block)
                if frame_count == calibration_frames:
                    threshold = self._adaptive_threshold(noise_calibration)
                pre_roll.append(block)
                return

            if not speech_started:
                pre_roll.append(block)
                if energy > threshold:
                    speech_started = True
                    print("[Audio] 🗣  Speech detected — recording...")
                    captured.extend(list(pre_roll))
                    pre_roll.clear()
            else:
                captured.append(block)
                if energy < threshold * 0.6:
                    silence_counter += 1
                    if silence_counter >= silence_limit:
                        stop_flag[0] = True
                else:
                    silence_counter = 0

            if frame_count >= max_frames:
                stop_flag[0] = True

        print("[Audio] 🎙  Calibrating microphone... please wait silently for 0.6s")
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=CHANNELS,
            blocksize=CHUNK,
            dtype=np.float32,
            callback=callback,
        ):
            deadline = time.time() + self.max_duration + 2.0
            while not stop_flag[0] and time.time() < deadline:
                sd.sleep(30)

        if not captured:
            raise RuntimeError("No speech captured. Check your microphone.")

        audio = np.concatenate(captured)
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.95

        pcm = (audio * 32767).astype(np.int16)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm.tobytes())

        duration = len(audio) / self.sample_rate
        print(f"[Audio] ✅ Saved {duration:.1f}s → {output_path}")
        return output_path
