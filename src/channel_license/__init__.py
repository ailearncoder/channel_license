"""license 包：导出核心模块供外部使用。"""

from . import config  # re-export for convenience
from . import database
from . import models
from . import logic
from . import exceptions
from . import api
from . import fastapi_app


def main() -> None:
    print("Hello from license package!")


__all__ = [
    "config",
    "database",
    "models",
    "logic",
    "exceptions",
    "api",
    "main",
    "fastapi_app",
]
