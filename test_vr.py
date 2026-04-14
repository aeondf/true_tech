import requests
import json

API_URL = "https://api.gpt.mws.ru/v1"
API_KEY = "sk-II90RLcfQeowlrusifVDbA"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ==== КОНКРЕТНЫЕ МОДЕЛИ ДЛЯ ТЕСТИРОВАНИЯ ====
MODELS_TO_TEST = {
    "audio": ["whisper-medium", "whisper-turbo-local"],
    "image_generation": ["qwen-image", "qwen-image-lightning"],
    "vision": ["qwen2.5-vl", "qwen3-vl-30b-a3b-instruct", "qwen2.5-vl-72b", "cotype-pro-vl-32b"]
}


# ==== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====

def format_response(text, max_length=2000):
    """Красивый вывод ответа с ограничением длины"""
    try:
        # Пробуем распарсить JSON для читаемого вывода
        data = json.loads(text)

        # Для генерации изображений
        if "data" in data and isinstance(data["data"], list):
            urls = [item.get("url", "N/A") for item in data["data"]]
            return f"🖼 Сгенерировано изображений: {len(urls)}\n" + "\n".join(f"   └─ {url}" for url in urls)

        # Для chat/vision ответов
        if "choices" in data:
            content = data["choices"][0].get("message", {}).get("content", "N/A")
            return f"💬 Ответ модели:\n   {content.strip()}"

        # Для транскрибации аудио
        if "text" in data:
            return f"🎤 Транскрибация:\n   {data['text'].strip()}"

        # fallback: красивый вывод всего JSON
        return json.dumps(data, ensure_ascii=False, indent=2)

    except json.JSONDecodeError:
        # Если не JSON — выводим как есть, с обрезкой если слишком длинный
        if len(text) > max_length:
            return text[:max_length] + f"\n\n... (ещё {len(text) - max_length} символов)"
        return text


# ==== ТЕСТЫ ====

def test_audio(model):
    """Тест распознавания аудио"""
    print(f"\n  🔹 Тест аудио: {model}")
    url = f"{API_URL}/audio/transcriptions"
    try:
        files = {
            "file": ("audio_2026-04-11_22-37-52.wav",
                     open("audio_2026-04-11_22-37-52.wav", "rb"),
                     "audio/wav")
        }
        data = {"model": model}
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {API_KEY}"},
            files=files,
            data=data,
            timeout=60
        )
        files["file"][1].close()

        print(f"  📡 Статус: {r.status_code}")
        print("  📝 Ответ:")
        print("  " + "-" * 50)
        print("  " + format_response(r.text).replace("\n", "\n  "))
        print("  " + "-" * 50)
        return r.status_code

    except FileNotFoundError:
        print("  ❌ Ошибка: файл audio_2026-04-11_22-37-52.wav не найден")
        return "ERROR"
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return "ERROR"


def test_image_generation(model):
    """Тест генерации изображений"""
    print(f"\n  🔹 Тест генерации: {model}")
    url = f"{API_URL}/images/generations"
    data = {
        "model": model,
        "prompt": "A cute cat sitting on a windowsill, digital art",
        "size": "1024x1024"
    }
    try:
        r = requests.post(url, headers=HEADERS, json=data, timeout=300)
        print(f"  📡 Статус: {r.status_code}")
        print("  📝 Ответ:")
        print("  " + "-" * 50)
        print("  " + format_response(r.text).replace("\n", "\n  "))
        print("  " + "-" * 50)
        return r.status_code
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return "ERROR"


def test_vision(model):
    """Тест анализа изображений (vision)"""
    print(f"\n  🔹 Тест vision: {model}")
    url = f"{API_URL}/chat/completions"
    data = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Что изображено на этой картинке? Опиши кратко на русском."},
                {"type": "image_url", "image_url": {"url": "https://i.ytimg.com/vi/sUMoFwHNu9g/maxresdefault.jpg"}}
            ]
        }],
        "max_tokens": 300
    }
    try:
        r = requests.post(url, headers=HEADERS, json=data, timeout=45)
        print(f"  📡 Статус: {r.status_code}")
        print("  📝 Ответ:")
        print("  " + "-" * 50)
        print("  " + format_response(r.text).replace("\n", "\n  "))
        print("  " + "-" * 50)
        return r.status_code
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return "ERROR"


# ==== ОСНОВНОЙ ПРОГОН ====

def run_tests():
    results = []

    # 🎵 Аудио
    print("\n" + "🎧" * 30)
    print("ТЕСТИРОВАНИЕ РАСПОЗНАВАНИЯ АУДИО")
    print("🎧" * 30)
    for model in MODELS_TO_TEST.get("audio", []):
        status = test_audio(model)
        results.append(("🎵 AUDIO", model, status))

    # 🖼 Генерация изображений
    print("\n" + "🎨" * 30)
    print("ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ")
    print("🎨" * 30)
    for model in MODELS_TO_TEST.get("image_generation", []):
        status = test_image_generation(model)
        results.append(("🖼 IMAGE_GEN", model, status))

    # 👁 Vision
    print("\n" + "👁" * 30)
    print("ТЕСТИРОВАНИЕ АНАЛИЗА ИЗОБРАЖЕНИЙ (VISION)")
    print("👁" * 30)
    for model in MODELS_TO_TEST.get("vision", []):
        status = test_vision(model)
        results.append(("👁 VISION", model, status))

    # 📊 Итоговый отчет
    print("\n" + "📊" * 30)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("📊" * 30)
    for test_type, model, status in results:
        status_str = f"✅ {status}" if status == 200 else f"❌ {status}"
        print(f"{test_type:14} | {model:40} | {status_str}")


if __name__ == "__main__":
    run_tests()
