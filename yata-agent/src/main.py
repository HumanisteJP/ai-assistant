"""Unified entrypoint that hosts both FastAPI (Google OAuth callback) and
Discord Bot in the **same** Python process & event loop (see plan-2.md).

Only the pieces required for automated tests are implemented at the
moment.  The Discord bot start-up and Uvicorn server execution are kept
behind the ``__main__`` guard so that importing this module does **not**
produce side-effects during test discovery.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from starlette.responses import HTMLResponse

# DI container -------------------------------------------------------------
from container import container  # type: ignore

# -------------------------------------------------------------------------
# FastAPI application
# -------------------------------------------------------------------------
app = FastAPI(title="Yata Agent OAuth Callback API")


# ----------------------------- Health check -----------------------------

@app.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    """Return a simple JSON payload indicating the service is alive.

    This endpoint is intentionally unauthenticated and should remain lightweight so that
    load balancers or uptime monitoring tools can poll it frequently.
    """
    return {"status": "ok"}


# ---------------------------- util helpers --------------------------------

def _parse_guild_id_from_state(state: str) -> int:
    """Extract the guild_id from the *state* parameter.

    The current format is ``"gid:<guild_id>"``. If the format is invalid
    this function raises :class:`ValueError`.
    """
    prefix = "gid:"
    if not state.startswith(prefix):
        raise ValueError("Invalid state format")
    try:
        return int(state[len(prefix) :])
    except ValueError as exc:
        raise ValueError("State does not contain a valid guild id") from exc


# ----------------------------- HTTP route ---------------------------------

@app.get("/oauth2callback", summary="Google OAuth2 callback")
async def oauth2callback(code: str, state: str):
    """Receive ``code`` & ``state`` from Google OAuth 2.0 flow.

    1. Extract ``guild_id`` from *state*
    2. Exchange *code* for Google credentials via
       ``GoogleService.exchange_code_for_credentials``.
    3. Return a minimal HTML response instructing the user they can close
       the tab.
    """

    try:
        guild_id = _parse_guild_id_from_state(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    google_service: Any | None = getattr(container, "google_service", None)
    if google_service is None:
        raise HTTPException(status_code=500, detail="GoogleService not configured")

    # Delegate to service.  Exceptions will propagate and FastAPI will
    # convert them into 500 responses, which is acceptable here.
    await google_service.exchange_code_for_credentials(guild_id=guild_id, code=code)

    # bilingual message
    html = (
        "<html><body style='font-family:sans-serif;'>"
        "<h3>✅ 認証に成功しました！ このタブは閉じて構いません。<br/>"
        "Authentication successful! You may close this tab.</h3>"
        "</body></html>"
    )
    return HTMLResponse(content=html, status_code=200)


# -------------------------------------------------------------------------
# Discord Bot – started only when executed as a script
# -------------------------------------------------------------------------
if __name__ == "__main__":
    import logging
    import uvicorn
    import discord
    from discord.ext import commands
    from dotenv import load_dotenv

    # .envファイルから環境変数を読み込む
    load_dotenv()
    
    # Setup logging - only essential logs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Reduce Discord.py logging to essential only
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    
    # Keep application logging at INFO level
    app_logger = logging.getLogger('cogs')
    app_logger.setLevel(logging.INFO)

    # --------------------------- setup DI ---------------------------------
    # Lazy imports to avoid heavy deps at import-time in unit tests.
    from data.database import Database
    from services.database_service import DatabaseService
    from services.google_service import GoogleService
    from services.transcription_service import TranscriptionService
    from services.processing_service import ProcessingService
    from services.audio_service import AudioService
    from services.readiness_service import ReadinessService

    # Load environment -----------------------------------------------------
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    CLIENT_SECRETS_JSON = os.getenv("CLIENT_SECRETS_JSON", "{}")
    REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/oauth2callback")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    DB_PATH = os.getenv("DB_PATH", "yata_agent.db")

    # Instantiate services -------------------------------------------------
    db = Database(DB_PATH)
    db_service = DatabaseService(db)

    google_service = GoogleService(
        db_service=db_service,
        client_secrets_json=CLIENT_SECRETS_JSON,
        redirect_uri=REDIRECT_URI,
    )
    container.google_service = google_service  # type: ignore[attr-defined]

    transcription_service = TranscriptionService(api_key=OPENAI_API_KEY)
    processing_service = ProcessingService(transcription_service, google_service, db_service)
    readiness_service = ReadinessService(db_service)

    audio_service = AudioService()

    # Store all services in the container for DI
    container.db_service = db_service
    container.google_service = google_service
    container.transcription_service = transcription_service
    container.processing_service = processing_service
    container.audio_service = audio_service
    container.readiness_service = readiness_service

    # Discord bot setup ----------------------------------------------------
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True  # Required for voice recording functionality
    bot = commands.Bot(command_prefix="/", intents=intents)

    # Inject container into bot so cogs can access shared services
    bot.container = container  # type: ignore[attr-defined]

    async def _startup():
        # Load cogs dynamically; in production you might scan a directory.
        bot.load_extension("cogs.setup_cog")
        bot.load_extension("cogs.recording_cog")
        bot.load_extension("cogs.auth_cog")
        bot.load_extension("cogs.status_cog")

    bot.loop.create_task(_startup())  # type: ignore[attr-defined]

    # Run FastAPI server inside the same loop
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    bot.loop.create_task(server.serve())  # type: ignore[attr-defined]

    # Finally, run the Discord bot (blocking until shutdown)
    print("Starting Yata Agent…")
    bot.run(DISCORD_TOKEN) 