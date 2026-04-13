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
    # Extended fields — not forwarded to MWS, consumed by proxy
    system_prompt: str | None = None       # memory block injected as system message
    conversation_id: str | None = None     # for history persistence
    use_memory: bool | None = True         # whether proxy should inject long-term memory


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
