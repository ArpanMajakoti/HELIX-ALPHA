import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


MODEL_PATH = "models/Qwen2.5-3B-Instruct-Q4_K_M.gguf"
SERVER_DIR = Path("llama_vulkan")
SERVER_EXE = "llama-server.exe"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8081
CONTEXT_SIZE = 2048
GPU_LAYERS = 99

HELIX_SYSTEM = (
    "You are Helix, a highly intelligent, calm, witty, and loyal AI assistant. "
    "Speak naturally, be concise, and occasionally slightly sarcastic when appropriate. "
    "Address the user as 'sir' occasionally. Never break character. "
    "Keep responses useful and focused."
)


class LLM:
    def __init__(
        self,
        model_path: str = MODEL_PATH,
        n_ctx: int = CONTEXT_SIZE,
        n_gpu_layers: int = GPU_LAYERS,
        verbose: bool = False,
    ):
        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"Model not found: {model_path}\n"
                "Download: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF"
            )
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.verbose = verbose
        self._proc = None
        self._cpu_llm = None
        self.mode = "cpu"
        self.backend = "llama-cpp-python (CPU)"
        self._start()

    def _server_exe(self):
        p = SERVER_DIR / SERVER_EXE
        return p if p.is_file() else None

    def _start(self):
        exe = self._server_exe()
        if exe:
            try:
                self._boot_vulkan(exe)
                return
            except Exception as err:
                print(f"[LLM] Warning: Vulkan failed ({err}), using CPU fallback.")
                self._kill_server()
        self._boot_cpu()

    def _boot_vulkan(self, exe: Path):
        print("[LLM] Starting Vulkan GPU server...")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self._proc = subprocess.Popen(
            [
                str(exe.absolute()),
                "--model", os.path.abspath(self.model_path),
                "--host", SERVER_HOST,
                "--port", str(SERVER_PORT),
                "-ngl", str(self.n_gpu_layers),
                "--ctx-size", str(self.n_ctx),
                "--no-mmap",
            ],
            stdout=subprocess.DEVNULL if not self.verbose else None,
            stderr=subprocess.DEVNULL if not self.verbose else None,
            creationflags=flags,
        )
        self._wait_ready(timeout=30)
        self.mode = "vulkan"
        self.backend = f"Vulkan GPU ({self.n_gpu_layers} layers offloaded)"
        print(f"[LLM] GPU acceleration ON: {self.backend}")

    def _wait_ready(self, timeout: int):
        url = f"http://{SERVER_HOST}:{SERVER_PORT}/health"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    if r.status == 200:
                        print(f"[LLM] Server ready at {SERVER_HOST}:{SERVER_PORT}")
                        return
            except (urllib.error.URLError, OSError):
                pass
            if self._proc and self._proc.poll() is not None:
                raise RuntimeError("llama-server process exited.")
            time.sleep(0.6)
        raise RuntimeError(f"Server not ready within {timeout}s")

    def _boot_cpu(self):
        print("[LLM] Loading CPU mode (llama-cpp-python)...")
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise ImportError("Run: pip install llama-cpp-python") from e
        self._cpu_llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=0,
            verbose=self.verbose,
        )
        self.mode = "cpu"
        self.backend = "llama-cpp-python CPU"
        print("[LLM] CPU model ready.")

    def _server_ok(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _build_messages(self, query: str, system: str, history: list) -> list:
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(history)
        msgs.append({"role": "user", "content": query.strip()})
        return msgs

    def _call_server(self, msgs: list, max_tokens: int, temperature: float, top_p: float) -> str:
        body = json.dumps({
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            f"http://{SERVER_HOST}:{SERVER_PORT}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        content = data["choices"][0]["message"].get("content")
        return (content or "").strip()

    def _stream_server(self, msgs, max_tokens, temperature, top_p):
        body = json.dumps({
            "messages": msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }).encode()
        req = urllib.request.Request(
            f"http://{SERVER_HOST}:{SERVER_PORT}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            buf = ""
            while True:
                chunk = r.read(1)
                if not chunk:
                    break
                buf += chunk.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line.startswith("data: "):
                        payload = line[6:]
                        if payload == "[DONE]":
                            return
                        try:
                            delta = json.loads(payload)["choices"][0]["delta"]
                            if delta.get("content") is not None:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            pass

    def _call_cpu(self, msgs, max_tokens, temperature, top_p) -> str:
        resp = self._cpu_llm.create_chat_completion(
            messages=msgs,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        content = resp["choices"][0]["message"].get("content")
        return (content or "").strip()

    def _stream_cpu(self, msgs, max_tokens, temperature, top_p):
        stream = self._cpu_llm.create_chat_completion(
            messages=msgs,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=True,
        )
        for chunk in stream:
            delta = chunk["choices"][0]["delta"]
            if delta.get("content") is not None:
                yield delta["content"]

    def generate(
        self,
        query: str,
        system_prompt: str = HELIX_SYSTEM,
        max_tokens: int = 512,
        temperature: float = 0.72,
        top_p: float = 0.9,
        history: list = None,
    ) -> str:
        if not (query and query.strip()):
            return "I didn't quite catch that, sir."
        msgs = self._build_messages(query, system_prompt, history or [])
        try:
            if self.mode == "vulkan" and self._server_ok():
                return self._call_server(msgs, max_tokens, temperature, top_p)
            return self._call_cpu(msgs, max_tokens, temperature, top_p)
        except Exception as e:
            print(f"[LLM] Error: {e}")
            return f"Apologies sir, I hit an error: {e}"

    def stream(
        self,
        query: str,
        system_prompt: str = HELIX_SYSTEM,
        max_tokens: int = 512,
        temperature: float = 0.72,
        top_p: float = 0.9,
        history: list = None,
    ):
        if not (query and query.strip()):
            yield "I didn't catch that, sir."
            return
        msgs = self._build_messages(query, system_prompt, history or [])
        try:
            if self.mode == "vulkan" and self._server_ok():
                yield from self._stream_server(msgs, max_tokens, temperature, top_p)
            else:
                yield from self._stream_cpu(msgs, max_tokens, temperature, top_p)
        except Exception as e:
            print(f"[LLM] Stream error: {e}")
            yield f"Apologies sir, I hit an error: {e}"

    def status(self) -> dict:
        return {
            "model": os.path.basename(self.model_path),
            "mode": self.mode,
            "backend": self.backend,
            "server_alive": self._server_ok(),
            "context": self.n_ctx,
        }

    def _kill_server(self):
        if self._proc and self._proc.poll() is None:
            try:
                if sys.platform == "win32":
                    self._proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
                self._proc.wait()

    def shutdown(self):
        if self._proc and self._proc.poll() is None:
            print("[LLM] Shutting down Vulkan server...")
            self._kill_server()
            print("[LLM] Server stopped.")

    def __del__(self):
        self.shutdown()
