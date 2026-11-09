from __future__ import annotations

import base64
import binascii
import logging
import os
import pathlib
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .autorefresh import start_scheduler
from .demo import demo_snapshot
from .pipeline import SNAPSHOT, read_json

load_dotenv()
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler_stop = start_scheduler()
    try:
        yield
    finally:
        if scheduler_stop is not None:
            scheduler_stop.set()


app = FastAPI(title="KOSPI Equity Screener", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.middleware("http")
async def optional_basic_auth(request: Request, call_next):
    if request.url.path == "/api/health":
        return await call_next(request)
    username = os.environ.get("BASIC_AUTH_USER", "").strip()
    password = os.environ.get("BASIC_AUTH_PASSWORD", "").strip()
    if bool(username) != bool(password):
        # Never accidentally publish unprotected content because a secret was omitted.
        return Response("Incomplete access configuration", status_code=503)
    if not username:
        return await call_next(request)
    auth = request.headers.get("Authorization", "")
    try:
        scheme, raw = auth.split(" ", 1)
        decoded = base64.b64decode(raw, validate=True).decode("utf-8") if scheme.lower() == "basic" else ""
        supplied_user, supplied_password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError, binascii.Error):
        supplied_user, supplied_password = "", ""
    if secrets.compare_digest(supplied_user, username) and secrets.compare_digest(supplied_password, password):
        return await call_next(request)
    return Response("Authentication required", status_code=401, headers={"WWW-Authenticate": 'Basic realm="KOSPI Lens", charset="UTF-8"'})


@app.get("/api/stocks")
def stocks():
    snapshot = read_json(SNAPSHOT)
    return JSONResponse(snapshot if snapshot else demo_snapshot(), headers={"Cache-Control": "no-store"})


@app.get("/api/health")
def health():
    snapshot = read_json(SNAPSHOT)
    return {"ok": True, "mode": snapshot.get("mode") if snapshot else "demo",
            "price_date": snapshot.get("price_date") if snapshot else None,
            "companies": len(snapshot.get("companies", [])) if snapshot else 0}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")
