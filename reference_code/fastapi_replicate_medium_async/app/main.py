from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi import APIRouter

from app.core.middlewares import RateLimitingMiddleware
from app.core.config import get_app_settings
from app.core.exception import add_exception_handlers
from app.core.logging import configure_logger
from app.api import (
    article,
    authentication,
    comment,
    health_check,
    profile,
    tag,
    user,
)





router = APIRouter()

router.include_router(router=health_check.router, tags=["Healthy Check"], prefix="/health-check")
router.include_router(router=authentication.router, tags=["Authentication"], prefix="/users")
router.include_router(router=user.router, tags=["User"], prefix="/user")
router.include_router(router=profile.router, tags=["Profiles"], prefix="/profiles")
router.include_router(router=tag.router, tags=["Tags"], prefix="/tags")
router.include_router(router=article.router, tags=["Articles"], prefix="/articles")
router.include_router(router=comment.router, tags=["Comments"], prefix="/articles")


def create_app() -> FastAPI:
    """
    Application factory, used to create application.
    """
    settings = get_app_settings()

    application = FastAPI(**settings.fastapi_kwargs)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RateLimitingMiddleware)

    application.include_router(router, prefix="/api")

    add_exception_handlers(app=application)

    configure_logger()


    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
