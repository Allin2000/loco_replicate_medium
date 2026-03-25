from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tag import TagService
from app.schemas.tag import TagListResponse # 导入 TagListResponse
from app.core.dep import container

router = APIRouter()


@router.get("", response_model=TagListResponse) # <-- 修改这里的 response_model 为 TagListResponse
async def get_all_tags(
    session: AsyncSession = Depends(container.session),
    tag_service: TagService = Depends(container.tag_service)
) -> TagListResponse: # <-- 修改这里的返回类型提示为 TagListResponse
    """
    Return available all tags.
    """
    # 获取 TagDTO 列表 (如果你的 TagService.list 返回 TagModel 列表，你需要转换)
    # 假设你的 tag_service.list 返回的是 TagModel 列表
    tag_models = await tag_service.list(session=session)

    # 从 TagModel 列表提取 tag 字符串
    # 如果 tag_models 可能是 None，需要处理一下
    if not tag_models:
        tags_list = []
    else:
        tags_list = [model.tag for model in tag_models]

    # 返回 TagListResponse 对象，包含 tags 键
    return TagListResponse(tags=tags_list) # <-- 包装成 TagListResponse 对象返回