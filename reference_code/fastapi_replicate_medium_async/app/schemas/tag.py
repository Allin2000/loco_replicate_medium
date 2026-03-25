import datetime
from typing import List

from pydantic import BaseModel

from app.sqlmodel.alembic_model import Tag



class TagDTO(BaseModel):
    id: int
    tag: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True  # Pydantic v2 正确写法

    @staticmethod
    def from_model(model: Tag) -> "TagDTO":
        return TagDTO(
            id=model.id,
            tag=model.tag,
            created_at=model.created_at
        )

    @staticmethod
    def to_model(dto: "TagDTO") -> Tag:
        model = Tag(tag=dto.tag)
        if hasattr(dto, "id"):
            model.id = dto.id
        return model
    

# --- 新增的 TagListResponse 模型 ---
class TagListResponse(BaseModel):
    tags: List[str] # 这是一个字符串列表，因为 Conduit API 返回的是标签名称列表



