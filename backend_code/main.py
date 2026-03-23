import os
import logging
import json
from pathlib import Path
from typing import Dict, Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
try:
    import sentry_sdk
except ModuleNotFoundError:
    sentry_sdk = None

try:
    from backend_code.auth import decode_access_token
    from backend_code.db import audit_log
    from backend_code.db import check_rate_limit
    from backend_code.db import create_notification
    from backend_code.db import save_chat_message
    from backend_code.db import mark_chat_message_delivered
    from backend_code.db import mark_chat_message_seen
    from backend_code.db import set_user_offline
    from backend_code.db import set_user_online
    from backend_code.routers.api_router import api_router
except ModuleNotFoundError:
    # Support running from backend_code/ with "uvicorn main:app --reload".
    from auth import decode_access_token
    from db import audit_log
    from db import check_rate_limit
    from db import create_notification
    from db import save_chat_message
    from db import mark_chat_message_delivered
    from db import mark_chat_message_seen
    from db import set_user_offline
    from db import set_user_online
    from routers.api_router import api_router

load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("socialsphere.main")

APP_NAME = os.getenv("APP_NAME", "Social Web App API")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
USE_LEGACY_FRONTEND_FALLBACK = os.getenv("USE_LEGACY_FRONTEND_FALLBACK", "false").strip().lower() in {"1", "true", "yes"}
FRONTEND_DIR_CANDIDATES = [PROJECT_ROOT / "frontend_react" / "dist"]
if USE_LEGACY_FRONTEND_FALLBACK:
    FRONTEND_DIR_CANDIDATES.append(PROJECT_ROOT / "frontend_code")
FRONTEND_DIR = next((path for path in FRONTEND_DIR_CANDIDATES if path.exists()), FRONTEND_DIR_CANDIDATES[0])
INDEX_FILE = FRONTEND_DIR / "index.html"

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Backend API for a social web application with authentication, posts, messaging, moderation, and admin capabilities.",
)

if SENTRY_DSN and sentry_sdk is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=max(0.0, min(SENTRY_TRACES_SAMPLE_RATE, 1.0)),
        environment=os.getenv("APP_ENV", "production"),
        release=APP_VERSION,
    )
elif SENTRY_DSN:
    logger.warning("sentry_dsn_provided_but_sdk_missing")

active_chat_connections: Dict[str, Set[WebSocket]] = {}
socket_users: Dict[WebSocket, str] = {}


def _user_has_any_socket(user_email: str) -> bool:
    return any(email == user_email for email in socket_users.values())


def _parse_dm_receiver(room: str, sender: str) -> str | None:
    # Expected format: dm:user1@example.com|user2@example.com
    if not room.startswith("dm:"):
        return None
    participants = [p.strip().lower() for p in room[3:].split("|") if p.strip()]
    if len(participants) != 2:
        return None
    if sender not in participants:
        return None
    return participants[0] if participants[1] == sender else participants[1]


async def _broadcast_room_event(room: str, payload: dict):
    serialized = json.dumps(payload)
    stale_connections = []
    for connection in active_chat_connections.get(room, set()):
        try:
            await connection.send_text(serialized)
        except Exception:
            stale_connections.append(connection)
    for stale in stale_connections:
        active_chat_connections.get(room, set()).discard(stale)
        stale_user = socket_users.pop(stale, None)
        if stale_user and not _user_has_any_socket(stale_user):
            set_user_offline(stale_user)

origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",") if origin.strip()]
if not origins:
    origins = ["*"]

allow_credentials = origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", tags=["root"])
async def root():
    if INDEX_FILE.exists():
        return FileResponse(str(INDEX_FILE))

    return {
        "message": "Welcome to Social Web App API",
        "status": "ok",
        "version": APP_VERSION,
    }


@app.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "app": APP_NAME,
    }


@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    decoded = decode_access_token(token)
    if not decoded:
        await websocket.close(code=1008)
        return

    sender_email = str(decoded.get("email", "")).lower().strip()
    room = str(websocket.query_params.get("room", "global")).strip() or "global"

    if room.startswith("dm:") and _parse_dm_receiver(room, sender_email) is None:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info("chat_connect sender=%s room=%s", sender_email, room)
    active_chat_connections.setdefault(room, set()).add(websocket)
    socket_users[websocket] = sender_email
    set_user_online(sender_email)
    try:
        while True:
            data = await websocket.receive_text()

            parsed = None
            if data.startswith("{"):
                try:
                    parsed = json.loads(data)
                except Exception:
                    parsed = None

            # Client acknowledgement that a message has been seen in the open room.
            if isinstance(parsed, dict) and parsed.get("type") == "seen":
                message_id = str(parsed.get("message_id", "")).strip()
                if message_id:
                    updated = mark_chat_message_seen(room=room, message_id=message_id, viewer_email=sender_email)
                    if updated is not None:
                        await _broadcast_room_event(
                            room,
                            {
                                "type": "chat_status",
                                "message": updated,
                            },
                        )
                continue

            message_text = str(parsed.get("text", "")).strip() if isinstance(parsed, dict) else str(data or "").strip()
            if not message_text:
                continue

            if not check_rate_limit("chat_send", sender_email, max_actions=80, window_seconds=60):
                logger.warning("chat_rate_limited sender=%s room=%s", sender_email, room)
                await websocket.send_text("system: Rate limit exceeded")
                continue

            stored_message = save_chat_message(room=room, from_user=sender_email, text=message_text)
            if stored_message is None:
                continue

            recipients = {
                socket_users.get(connection, "")
                for connection in active_chat_connections.get(room, set())
                if socket_users.get(connection, "") and socket_users.get(connection, "") != sender_email
            }
            # For DM rooms, this set should contain only one recipient; for group rooms it can contain many.
            for receiver in recipients:
                create_notification(
                    user_email=receiver,
                    notification_type="message",
                    from_user=sender_email,
                    title=f"New message from {sender_email} in {room}",
                )
                stored_message = mark_chat_message_delivered(room=room, message_id=stored_message.get("id", ""), receiver_email=receiver) or stored_message

            audit_log("chat_message", actor=sender_email, target=room)
            logger.info("chat_message sender=%s room=%s", sender_email, room)
            await _broadcast_room_event(
                room,
                {
                    "type": "chat_message",
                    "message": stored_message,
                },
            )
    except WebSocketDisconnect:
        logger.info("chat_disconnect sender=%s room=%s", sender_email, room)
        active_chat_connections.get(room, set()).discard(websocket)
        socket_users.pop(websocket, None)
        if not _user_has_any_socket(sender_email):
            set_user_offline(sender_email)
    except Exception:
        logger.exception("chat_error sender=%s room=%s", sender_email, room)
        active_chat_connections.get(room, set()).discard(websocket)
        socket_users.pop(websocket, None)
        if not _user_has_any_socket(sender_email):
            set_user_offline(sender_email)


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    if full_path.startswith("api") or full_path in {"health", "docs", "openapi.json", "redoc"}:
        raise HTTPException(status_code=404, detail="Not found")

    if FRONTEND_DIR.exists():
        requested = FRONTEND_DIR / full_path
        if requested.exists() and requested.is_file():
            return FileResponse(str(requested))
        if INDEX_FILE.exists():
            return FileResponse(str(INDEX_FILE))

    raise HTTPException(status_code=404, detail="Not found")
