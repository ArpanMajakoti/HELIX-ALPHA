import sys
import threading
from dotenv import load_dotenv
from audio import AudioManager
from speechtt import SpeechToText
from llm import LLM, HELIX_SYSTEM


load_dotenv()

BANNER = r"""
  ██╗  ██╗███████╗██╗     ██╗██╗  ██╗     █████╗ ██╗     ██████╗ ██╗  ██╗ █████╗
  ██║  ██║██╔════╝██║     ██║╚██╗██╔╝    ██╔══██╗██║     ██╔══██╗██║  ██║██╔══██╗
  ███████║█████╗  ██║     ██║ ╚███╔╝     ███████║██║     ██████╔╝███████║███████║
  ██╔══██║██╔══╝  ██║     ██║ ██╔██╗     ██╔══██║██║     ██╔═══╝ ██╔══██║██╔══██║
  ██║  ██║███████╗███████╗██║██╔╝ ██╗    ██║  ██║███████╗██║     ██║  ██║██║  ██║
  ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝
                            [ v1.0.0 — Voice AI Assistant ]
"""

EXIT_WORDS = {"exit", "quit", "goodbye", "shut down", "shutdown", "stop"}


def print_banner():
    print(BANNER)
    print("  🎙  Say something to Helix. Say 'exit' or press Ctrl+C to stop.\n")


def init_components():
    print("[Helix] Loading speech recognition...")
    stt = SpeechToText()

    print("[Helix] Initializing microphone...")
    audio = AudioManager()

    print("[Helix] Loading language model (may take 15-30s)...")
    llm = LLM()

    info = llm.status()
    print(f"[Helix] Mode: {info['backend']}")
    print(f"\n[Helix] ✅ All systems online. Listening...\n")

    return audio, stt, llm


def is_exit(text: str) -> bool:
    low = text.lower().strip()
    return any(low == w or low.startswith(w + " ") for w in EXIT_WORDS)


def main():
    print_banner()

    try:
        audio, stt, llm = init_components()
    except Exception as e:
        print(f"\n[FATAL] Could not start: {e}")
        sys.exit(1)

    conversation = []

    while True:
        try:
            print("─" * 60)
            audio_path = audio.record_until_silence()

            text = stt.transcribe(audio_path)
            if not text:
                print("⚠  No speech detected — try again.\n")
                continue

            print(f"\n  🧑 You  →  {text}\n")

            if is_exit(text):
                print("  🤖 Helix  →  Goodbye, sir. Shutting down.\n")
                break

            print("  🤖 Helix  →  ", end="", flush=True)
            full_reply = ""
            for token in llm.stream(text, history=conversation):
                print(token, end="", flush=True)
                full_reply += token
            print("\n")

            conversation.append({"role": "user", "content": text})
            conversation.append({"role": "assistant", "content": full_reply})

            if len(conversation) > 40:
                conversation = conversation[-40:]

        except KeyboardInterrupt:
            print("\n\n[Helix] Interrupted. Goodbye, sir.")
            break
        except RuntimeError as e:
            print(f"\n⚠  Audio error: {e}\n")
        except Exception as e:
            print(f"\n[Error] {e}\n")

    llm.shutdown()
    sys.exit(0)


if __name__ == "__main__":
    main()
