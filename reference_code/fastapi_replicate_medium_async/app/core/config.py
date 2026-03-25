from functools import lru_cache

from app.core.settings.app import AppSettings
from app.core.settings.base import AppEnvTypes, BaseAppSettings
from app.core.settings.development import DevAppSettings
from app.core.settings.production import ProdAppSettings
from app.core.settings.test import TestAppSettings

AppEnvType = DevAppSettings | TestAppSettings | ProdAppSettings

environments: dict[str, type[AppEnvType]] = {  # type: ignore
    AppEnvTypes.development: DevAppSettings,
    AppEnvTypes.testing: TestAppSettings,
    AppEnvTypes.production: ProdAppSettings,
}


@lru_cache
def get_app_settings() -> AppSettings:
    """
    Return application config.
    """
    app_env = BaseAppSettings().app_env
    config = environments[app_env]
    return config()  # type: ignore
