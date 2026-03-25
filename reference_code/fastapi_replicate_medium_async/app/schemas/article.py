import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from app.core.date import convert_datetime_to_realworld

DEFAULT_ARTICLES_LIMIT = 20
DEFAULT_ARTICLES_OFFSET = 0


# DTO改造1
class ArticleRecordDTO(BaseModel):
    id: int
    author_id: int
    slug: str
    title: str
    description: str
    body: str
    created_at: datetime.datetime
    updated_at: datetime.datetime



# DTO改造5
# 请求体（创建文章）请求CreateArticleData和DTO使用同一个数据模型
class CreateArticleDTO(BaseModel):
    title: str
    description: str
    body: str
    tags: List[str] = Field(alias="tagList")


# 单独请求模型定义 需提供DTO转换
class CreateArticleRequest(BaseModel):
    article: CreateArticleDTO

    def to_dto(self) -> CreateArticleDTO:
        # 不需要额外转换，直接返回内部字段即可
        return self.article

# DTO改造6
# 请求体（更新文章）
class UpdateArticleDTO(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    body: Optional[str] = None
    tags: Optional[List[str]] = Field(default=None, alias="tagList")

    def with_updated_fields(self, updated_fields: dict) -> "ArticleDTO":
        # 使用 Pydantic 的 copy(update=...) 替代 dataclasses.replace
        return self.copy(update=updated_fields)

# 单独请求模型定义
class UpdateArticleData(BaseModel):
    title: str | None = Field(None)
    description: str | None = Field(None)
    body: str | None = Field(None)


# 单独请求模型定义 需提供DTO转换
class UpdateArticleRequest(BaseModel):
    article: UpdateArticleDTO

    def to_dto(self) -> UpdateArticleDTO:
        # 同样不需要转换，DTO结构已统一
        return self.article


# 查询过滤器  单独请求响应
class ArticlesFilters(BaseModel):
    tag: Optional[str] = None
    author: Optional[str] = None
    favorited: Optional[str] = None
    limit: int = Field(DEFAULT_ARTICLES_LIMIT, ge=1)
    offset: int = Field(DEFAULT_ARTICLES_OFFSET, ge=0)


# DTO改造2
# 作者信息  响应ArticleAuthorData和DTO使用同一个数据模型
class ArticleAuthorDTO(BaseModel):
    username: str
    bio: str = ""
    image: Optional[str] = None
    following: bool = False
    id: Optional[int] = None

# DTO改造3
# 单篇文章数据 响应ArticleData和DTO使用同一个数据模型
class ArticleDTO(BaseModel):
    id: int
    author_id: int
    slug: str
    title: str
    description: str
    body: str
    tags: List[str] = Field(alias="tagList")
    author: ArticleAuthorDTO
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")
    favorited: bool = False
    favorites_count: int = Field(default=0, alias="favoritesCount")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime.datetime: convert_datetime_to_realworld},
    )



# 响应格式（单篇） 需提供DTO转换
class ArticleResponse(BaseModel):
    article: ArticleDTO

    @classmethod
    def from_dto(cls, dto: ArticleDTO) -> "ArticleResponse":
        return cls(article=dto)

# DTO改造4
# 响应格式（多篇） 响应ArticlesFeedResponse和DTO使用同一个数据 需提供DTO转换
class ArticlesFeedDTO(BaseModel):
    articles: List[ArticleDTO]
    articles_count: int = Field(alias="articlesCount")

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_articles(cls, articles: List[ArticleDTO]) -> "ArticlesFeedDTO":
        return cls(articles=articles, articlesCount=len(articles))


