import logging

import structlog
from structlog.typing import EventDict, Processor

from app.core.config import get_app_settings

__all__ = ["configure_logger"]

DEFAULT_LOGGER_NAME = "conduit-api"

settings = get_app_settings()


def rename_event_key(_: logging.Logger, __: str, event_dict: EventDict) -> EventDict:
    """
    Rename `event` field to `message`.
    """
    event_dict["message"] = event_dict.pop("event")
    return event_dict


def drop_color_message_key(
    _: logging.Logger, __: str, event_dict: EventDict
) -> EventDict:
    """
    Uvicorn logs the message a second time in the extra `color_message`, but we don't
    need it.
    This processor drops the key from the event dict if it exists.
    """
    event_dict.pop("color_message", None)
    return event_dict


def configure_logger(json_logs: bool = False) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # We rename the `event` key to `message` only in JSON logs.
        shared_processors.append(rename_event_key)
        # Format the exception only for JSON logs, as we want to pretty-print them when
        # using the ConsoleRenderer.
        shared_processors.append(structlog.processors.format_exc_info)

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    log_renderer = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer()
    )

    _configure_default_logging_by_custom(shared_processors, log_renderer)


def _configure_default_logging_by_custom(
    shared_processors: list[Processor], log_renderer: structlog.types.Processor
) -> None:
    # Use `ProcessorFormatter` to format all `logging` entries.
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            # Remove _record & _from_structlog.
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            log_renderer,
        ],
    )

    handler = logging.StreamHandler()
    # Use structlog `ProcessorFormatter` to format all `logging` entries.
    handler.setFormatter(formatter)

    # Disable the `passlib` logger.
    logging.getLogger("passlib").setLevel(logging.ERROR)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Set logging level.
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.logging_level)

    for _log in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        # Clear the log handlers for uvicorn loggers, and enable propagation
        # so the messages are caught by our root logger and formatted correctly
        # by structlog.
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True






#  # 保存日志到文件 configure_logger(log_file_path="app_logs.txt")

# import logging
# import structlog
# from structlog.typing import EventDict, Processor

# from app.core.config import get_app_settings

# __all__ = ["configure_logger"]

# DEFAULT_LOGGER_NAME = "conduit-api"

# settings = get_app_settings()


# def rename_event_key(_: logging.Logger, __: str, event_dict: EventDict) -> EventDict:
#     """
#     Rename `event` field to `message`.
#     """
#     event_dict["message"] = event_dict.pop("event")
#     return event_dict


# def drop_color_message_key(
#     _: logging.Logger, __: str, event_dict: EventDict
# ) -> EventDict:
#     """
#     Uvicorn logs the message a second time in the extra `color_message`, but we don't
#     need it.
#     This processor drops the key from the event dict if it exists.
#     """
#     event_dict.pop("color_message", None)
#     return event_dict


# def configure_logger(json_logs: bool = False, log_file_path: str = None) -> None: # <--- 添加 log_file_path 参数
#     timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")

#     shared_processors: list[Processor] = [
#         structlog.contextvars.merge_contextvars,
#         structlog.stdlib.add_logger_name,
#         structlog.stdlib.add_log_level,
#         structlog.stdlib.PositionalArgumentsFormatter(),
#         structlog.stdlib.ExtraAdder(),
#         drop_color_message_key,
#         timestamper,
#         structlog.processors.StackInfoRenderer(),
#     ]

#     if json_logs:
#         shared_processors.append(rename_event_key)
#         shared_processors.append(structlog.processors.format_exc_info)

#     structlog.configure(
#         processors=shared_processors
#         + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
#         logger_factory=structlog.stdlib.LoggerFactory(),
#         cache_logger_on_first_use=True,
#     )

#     log_renderer = (
#         structlog.processors.JSONRenderer()
#         if json_logs
#         else structlog.dev.ConsoleRenderer()
#     )

#     _configure_default_logging_by_custom(shared_processors, log_renderer, log_file_path) # <--- 传递 log_file_path


# def _configure_default_logging_by_custom(
#     shared_processors: list[Processor], log_renderer: structlog.types.Processor, log_file_path: str = None # <--- 接收 log_file_path
# ) -> None:
#     formatter = structlog.stdlib.ProcessorFormatter(
#         foreign_pre_chain=shared_processors,
#         processors=[
#             structlog.stdlib.ProcessorFormatter.remove_processors_meta,
#             log_renderer,
#         ],
#     )

#     # 根据 log_file_path 是否存在来选择使用 StreamHandler 还是 FileHandler
#     if log_file_path:
#         handler = logging.FileHandler(log_file_path) # <--- 使用 FileHandler
#     else:
#         handler = logging.StreamHandler() # <--- 默认仍然输出到控制台

#     handler.setFormatter(formatter)

#     logging.getLogger("passlib").setLevel(logging.ERROR)
#     logging.getLogger("asyncio").setLevel(logging.WARNING)

#     root_logger = logging.getLogger()
#     root_logger.addHandler(handler)
#     root_logger.setLevel(settings.logging_level)

#     for _log in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
#         logging.getLogger(_log).handlers.clear()
#         logging.getLogger(_log).propagate = True
