from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.realtime.lifespan import lifespan
from app.realtime.router import router


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    app = FastAPI(title=f"{app_settings.PROJECT_NAME} realtime", lifespan=lifespan)
    app.state.settings = app_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()
