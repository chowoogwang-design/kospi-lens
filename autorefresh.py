"""Run a single-service scheduled EOD refresh using only Python's stdlib.

A Render cron job cannot access the web service's persistent disk; the paid web
service refreshes its own disk. Keep uvicorn at one worker to avoid duplicates.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import threading
from zoneinfo import ZoneInfo

from .pipeline import Credentials, build_live_snapshot

log = logging.getLogger("kospi.refresh")
KST = ZoneInfo("Asia/Seoul")
_refresh_lock = threading.Lock()


def refresh_now():
    if not _refresh_lock.acquire(blocking=False):
        log.info("Another refresh is underway; skipping duplicate")
        return
    try:
        keys = Credentials(os.getenv("KRX_API_KEY", "").strip(), os.getenv("DART_API_KEY", "").strip())
        if not keys.krx or not keys.dart:
            log.warning("Missing KRX/DART API keys; continuing in labelled demo mode")
            return
        log.info("Starting KRX and OpenDART daily refresh")
        result = build_live_snapshot(keys, on_progress=log.info)
        log.info("Saved %s verified issuer rows for price date %s", len(result["companies"]), result["price_date"])
    except Exception:
        # The previous successful saved snapshot is deliberately retained.
        log.exception("Live refresh failed: previous successful snapshot retained")
    finally:
        _refresh_lock.release()


def schedule_due(now: dt.datetime, last_scheduled_date: dt.date | None) -> bool:
    """True after 08:30 KST on weekdays, once per local calendar date."""
    local = now.astimezone(KST)
    return (local.weekday() < 5 and (local.hour, local.minute) >= (8, 30)
            and local.date() != last_scheduled_date)


def start_scheduler():
    """Start background refresh immediately and at 08:30 KST every weekday.

    The startup refresh runs on a daemon thread so the site serves immediately.
    Its result replaces the demo after completion; browsing then reloads the page.
    """
    if os.getenv("AUTO_REFRESH", "0").strip().lower() not in ("1", "true", "yes"):
        return None
    stop = threading.Event()

    def loop():
        # On startup, perform a refresh independent of the daily 08:30 schedule.
        # Skip a second immediate run if startup already happened after 08:30.
        now = dt.datetime.now(KST)
        last_date = now.date() if schedule_due(now, None) else None
        refresh_now()
        while not stop.wait(60):
            now = dt.datetime.now(KST)
            if schedule_due(now, last_date):
                last_date = now.date()
                refresh_now()

    worker = threading.Thread(target=loop, name="kospi-daily-refresh", daemon=True)
    worker.start()
    log.info("Auto-refresh enabled: weekdays 08:30 Asia/Seoul plus an initial refresh")
    return stop
