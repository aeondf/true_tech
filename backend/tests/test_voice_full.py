"""
Полный E2E тест голосового пайплайна:
  Audio → ASR (whisper-turbo-local) → Router → LLM → TTS → аудио-ответ

Использует реальный голосовой файл voice_sample.mp3 (русская речь).
Сохраняет аудио-ответ в /tmp/voice_response_out.wav (или .mp3).

Запуск:
  source .venv/bin/activate
  python backend/tests/test_voice_full.py
"""
import os
import time
import asyncio
import httpx

BASE = "http://localhost:8000"
TIMEOUT = 120
AUDIO_FILE = os.path.join(os.path.dirname(__file__), "voice_sample.mp3")


def ok(name: str, status: int, elapsed: float, extra: str = ""):
    sym = "✅" if 200 <= status < 400 else "❌"
    print(f"  {sym} [{status}] {name} ({elapsed:.1f}s){' — ' + extra if extra else ''}")


def fail(name: str, msg: str):
    print(f"  ❌ {name} — {msg}")


async def run_tests():
    results = []

    print()
    print("🎤 Голосовой файл:", AUDIO_FILE)
    print("   Размер:", os.path.getsize(AUDIO_FILE), "байт")
    print()

    with open(AUDIO_FILE, "rb") as f:
        audio_bytes = f.read()

    # ── 1. ASR напрямую → MWS ────────────────────────────────────
    print("═" * 60)
    print("1. ASR напрямую → MWS whisper-turbo-local")
    print("═" * 60)

    try:
        key = ""
        try:
            for line in open("backend/.env"):
                if line.startswith("MWS_API_KEY="):
                    key = line.strip().split("=", 1)[1]
        except FileNotFoundError:
            pass

        if not key:
            fail("MWS ASR direct", "MWS_API_KEY не найден в backend/.env")
            results.append(("MWS ASR direct", False))
        else:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=TIMEOUT) as c:
                r = await c.post(
                    "https://api.gpt.mws.ru/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {key}"},
                    files={"file": ("voice_sample.mp3", audio_bytes, "audio/mpeg")},
                    data={"model": "whisper-turbo-local"},
                )
            elapsed = time.time() - t0
            text = r.json().get("text", "") if r.status_code == 200 else ""
            ok("MWS ASR direct", r.status_code, elapsed, f"transcript={text!r}")
            results.append(("MWS ASR direct", r.status_code == 200 and bool(text)))
    except Exception as e:
        fail("MWS ASR direct", str(e))
        results.append(("MWS ASR direct", False))

    # ── 2. Полный голосовой пайплайн ─────────────────────────────
    print()
    print("═" * 60)
    print("2. Полный пайплайн — POST /v1/voice/message")
    print("   Audio → ASR → Router → LLM → TTS → аудио-ответ")
    print("═" * 60)

    try:
        t0 = time.time()
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.post(
                f"{BASE}/v1/voice/message",
                files={"audio": ("voice_sample.mp3", audio_bytes, "audio/mpeg")},
                data={"user_id": "test-voice"},
            )
        elapsed = time.time() - t0

        if r.status_code == 200:
            transcript = r.headers.get("x-transcript", "")
            answer = r.headers.get("x-answer", "")
            ct = r.headers.get("content-type", "")

            if "audio" in ct:
                # TTS сработал — сохраняем аудио-ответ
                ext = "wav" if "wav" in ct else "mp3"
                out_path = f"/tmp/voice_response_out.{ext}"
                with open(out_path, "wb") as f:
                    f.write(r.content)
                ok("Voice pipeline", r.status_code, elapsed,
                   f"transcript={transcript!r}")
                print(f"    🎙️  Транскрипт: {transcript}")
                print(f"    🤖  Ответ LLM:  {answer[:120]}")
                print(f"    🔊  Аудио-ответ ({ct}): {len(r.content)} байт")
                print(f"    📁  Сохранён:   {out_path}")
                results.append(("Voice pipeline (with TTS audio)", True))
            else:
                # TTS недоступен — вернулся JSON
                data = r.json()
                transcript = data.get("transcript", "")
                answer = data.get("answer", "")
                ok("Voice pipeline (TTS fallback → JSON)", r.status_code, elapsed)
                print(f"    🎙️  Транскрипт: {transcript!r}")
                print(f"    🤖  Ответ LLM:  {answer[:120]}")
                print(f"    ⚠️  TTS недоступен (tts_available=false)")
                # Считаем успехом если ASR + LLM отработали
                results.append(("Voice pipeline (ASR+LLM)", bool(transcript or answer)))
        else:
            ok("Voice pipeline", r.status_code, elapsed, r.text[:150])
            results.append(("Voice pipeline", False))
    except Exception as e:
        fail("Voice pipeline", str(e))
        results.append(("Voice pipeline", False))

    # ── 3. WebSocket голосовой чат ───────────────────────────────
    print()
    print("═" * 60)
    print("3. WebSocket /ws/voice")
    print("═" * 60)

    try:
        import websockets, json as _json
        t0 = time.time()
        async with websockets.connect("ws://localhost:8000/v1/ws/voice", close_timeout=5) as ws:
            await ws.send(audio_bytes)

            transcript = ""
            tokens = []
            audio_received = False

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT)
                    if isinstance(msg, bytes):
                        audio_received = True
                        ext = "wav"
                        with open(f"/tmp/ws_voice_response.{ext}", "wb") as f:
                            f.write(msg)
                        print(f"    🔊  Аудио-ответ: {len(msg)} байт → /tmp/ws_voice_response.{ext}")
                        break
                    data = _json.loads(msg)
                    t = data.get("type")
                    if t == "transcript":
                        transcript = data.get("text", "")
                        print(f"    🎙️  Транскрипт: {transcript!r}")
                    elif t == "token":
                        tokens.append(data.get("text", ""))
                    elif t in ("done", "error"):
                        print(f"    ℹ️  {data}")
                        break
                except asyncio.TimeoutError:
                    break

        elapsed = time.time() - t0
        answer = "".join(tokens)
        ok("WebSocket voice", 200, elapsed,
           f"answer={answer[:80]!r}, audio={'✅' if audio_received else '❌ (TTS unavailable)'}")
        results.append(("WebSocket voice", bool(transcript or answer)))
    except ImportError:
        print("  ⚠️  websockets не установлен (pip install websockets) — пропускаю")
        results.append(("WebSocket voice", None))
    except Exception as e:
        fail("WebSocket voice", str(e))
        results.append(("WebSocket voice", False))

    # ── Summary ──────────────────────────────────────────────────
    print()
    print("═" * 60)
    print("ИТОГО — Голосовой пайплайн")
    print("═" * 60)
    for name, passed in results:
        if passed is None:
            print(f"  ⚠️  {name} — пропущен")
        elif passed:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name}")

    total  = sum(1 for _, p in results if p is True)
    failed = sum(1 for _, p in results if p is False)
    skip   = sum(1 for _, p in results if p is None)
    print(f"\n  Passed: {total}  Failed: {failed}  Skipped: {skip}")


if __name__ == "__main__":
    asyncio.run(run_tests())
