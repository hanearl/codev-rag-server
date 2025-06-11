from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: Role
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[ChatCompletionUsage] = None


class CompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    prompt: Union[str, List[str]]
    max_tokens: Optional[int] = Field(default=16, gt=0)
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    n: Optional[int] = Field(default=1, gt=0)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None


class CompletionChoice(BaseModel):
    text: str
    index: int
    finish_reason: Optional[str] = None


class CompletionResponse(BaseModel):
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: Optional[ChatCompletionUsage] = None 