import datetime
from typing import List

from pydantic import BaseModel, Field, ConfigDict

from app.core.date import convert_datetime_to_realworld
from app.schemas.profile import ProfileDTO

# DTO改造 4
# 创建评论请求体 请求CreateCommentData和DTO公用一个数据模型
class CreateCommentDTO(BaseModel):
    body: str

# 单独请求 需要提供DTO转换
class CreateCommentRequest(BaseModel):
    comment: CreateCommentDTO

    def to_dto(self) -> CreateCommentDTO:
        return CreateCommentDTO(body=self.comment.body)


# DTO改造 1
class CommentRecordDTO(BaseModel):
    id: int
    body: str
    author_id: int
    article_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


# DTO改造 2
class CommentDTO(BaseModel):
    id: int
    body: str
    author:ProfileDTO

    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime.datetime: convert_datetime_to_realworld}
    )




# DTO改造 3
class CommentsListDTO(BaseModel):
    comments: List[CommentDTO]
    comments_count: int = Field(alias="commentsCount")

    model_config = ConfigDict(populate_by_name=True)




# 单独响应请求
class CommentAuthorData(BaseModel):
    username: str
    bio: str
    image: str | None
    following: bool

# 单独响应请求
class CommentData(BaseModel):
    id: int
    body: str
    author: CommentAuthorData
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")

    model_config = ConfigDict(
        json_encoders={datetime.datetime: convert_datetime_to_realworld}
    )


# 单独响应请求
class CommentResponse(BaseModel):
    comment: CommentData

    @classmethod
    def from_dto(cls, dto: CommentDTO) -> "CommentResponse":
        comment = CommentData(
            id=dto.id,
            body=dto.body,
            createdAt=dto.created_at,
            updatedAt=dto.updated_at,
            author=CommentAuthorData(
                username=dto.author.username,
                bio=dto.author.bio,
                image=dto.author.image,
                following=dto.author.following,
            ),
        )
        return CommentResponse(comment=comment)
    

# 单独响应请求
class CommentsListResponse(BaseModel):
    comments: list[CommentData]
    commentsCount: int

    @classmethod
    def from_dto(cls, dto: CommentsListDTO) -> "CommentsListResponse":
        comments = [
            CommentResponse.from_dto(dto=comment_dto).comment
            for comment_dto in dto.comments
        ]
        return CommentsListResponse(comments=comments, commentsCount=dto.comments_count)