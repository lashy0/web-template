from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LogSettings(BaseSettings):
    """What the application logs and in which format."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    level: LogLevel = Field(
        default="INFO",
        validation_alias="BACKEND_LOG_LEVEL",
        description="Lowest level written by the application and the libraries without a level of their own.",
    )

    json_output: bool = Field(
        default=False,
        validation_alias="BACKEND_LOG_JSON",
        description=(
            "Write JSON even in a terminal. Without a terminal (containers, CI) logs are JSON anyway; "
            "in a terminal they are readable text."
        ),
    )

    sqlalchemy_level: LogLevel = Field(
        default="WARNING",
        validation_alias="BACKEND_LOG_SQLALCHEMY_LEVEL",
        description="Level of SQLAlchemy engine and pool logs; INFO writes every SQL statement.",
    )

    saq_level: LogLevel = Field(
        default="WARNING",
        validation_alias="BACKEND_LOG_SAQ_LEVEL",
        description="Level of the task queue logs; INFO writes every job, including scheduled ones each minute.",
    )
