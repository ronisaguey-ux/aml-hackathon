from typing import List, Optional, Union, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


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


def parse_timestamp_to_ms(val: Any) -> Optional[int]:
    """Parse various timestamp representations into integer unix milliseconds."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        # Try integer / float string
        try:
            return int(float(val_str))
        except ValueError:
            pass
        # Try ISO format (e.g. 2024-01-01T00:00:00Z)
        try:
            dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except Exception:
            return None
    return None


class MessageItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str
    content: Union[str, List[Any], Dict[str, Any]]
    timestamp: Optional[Union[int, float, str]] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, v):
        return parse_timestamp_to_ms(v)

    def get_text_content(self) -> str:
        return normalize_content(self.content)


class AddRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str
    messages: List[MessageItem]
    user_id: str
    session_id: str


class AddResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool
    request_id: str
    user_id: str
    session_id: str


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query: Union[str, List[Any], Dict[str, Any]]
    options: Optional[List[str]] = None
    user_id: str
    top_k: int = 100

    def get_query_text(self) -> str:
        return normalize_content(self.query)


class MemoryResultItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    content: str
    score: Optional[float] = None
    created_at: Optional[str] = None


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: List[MemoryResultItem] = Field(default_factory=list)
