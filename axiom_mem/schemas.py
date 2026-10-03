from typing import List, Optional, Union, Any, Dict
from pydantic import BaseModel, Field


def normalize_content(content: Union[str, List[Any], Dict[str, Any]]) -> str:
    """Normalize content into a string, gracefully handling Multimodal ContentPart[] or dicts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # E.g. {"type": "text", "text": "..."}
                if "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return " ".join(parts)
    if isinstance(content, dict):
        if "text" in content:
            return str(content["text"])
        if "content" in content:
            return str(content["content"])
        return str(content)
    return str(content)


class MessageItem(BaseModel):
    role: str
    content: Union[str, List[Any], Dict[str, Any]]
    timestamp: Optional[int] = None

    def get_text_content(self) -> str:
        return normalize_content(self.content)


class AddRequest(BaseModel):
    request_id: str
    messages: List[MessageItem]
    user_id: str
    session_id: str


class AddResponse(BaseModel):
    success: bool
    request_id: str
    user_id: str
    session_id: str


class SearchRequest(BaseModel):
    query: Union[str, List[Any], Dict[str, Any]]
    options: Optional[List[str]] = None
    user_id: str
    top_k: int = 100

    def get_query_text(self) -> str:
        return normalize_content(self.query)


class MemoryResultItem(BaseModel):
    id: str
    content: str
    score: Optional[float] = None
    created_at: Optional[str] = None


class SearchResponse(BaseModel):
    data: List[MemoryResultItem] = Field(default_factory=list)
