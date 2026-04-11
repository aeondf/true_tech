import requests

API_KEY = "sk-ewgiaPC3A6pPDYHwR8siVA"
BASE_URL = "https://api.gpt.mws.ru/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

data = {
    "model": "qwen3-coder-480b-a35b",
    "messages": [
        {"role": "system", "content": "Ты полезный ассистент"},
        {"role": "user", "content": "Объясни, как работает API MWS GPT"}
    ],
    "temperature": 0.3,
    "max_tokens": 300,
}

response = requests.post(f"{BASE_URL}/chat/completions", headers=headers, json=data)

print("Status:", response.status_code)
print(response.text)
