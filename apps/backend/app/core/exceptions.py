from typing import Any, ClassVar


class AppError(Exception):
    """Base class for expected application errors."""

    code: ClassVar[str] = "application_error"
    default_message: ClassVar[str] = "application error"

    def __init__(
        self,
        message: str | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details

        super().__init__(self.message)
