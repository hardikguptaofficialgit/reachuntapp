"""FastAPI entry — use api.server for uvicorn."""

from api.app_factory import create_app

app = create_app()
