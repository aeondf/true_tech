from typing import Any
from pydantic import BaseModel


class Message(BaseModel):
    role: str   # system | user | assistant
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    temperature: float | None = None
    max_tokens: int | None = None
    n: int | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    stream: bool = False
    user: str | None = None


class CompletionRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    stop: list[str] | None = None
    stream: bool = False


class EmbeddingRequest(BaseModel):
    model: str
    input: str | list[str]
