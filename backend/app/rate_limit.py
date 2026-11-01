import hashlib
import time

from fastapi import HTTPException, Request
from sqlalchemy import case, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session as DBSession

from .models import AuthRateLimitBucket

LOGIN_LIMIT = 5
LOGIN_WINDOW_SECONDS = 15 * 60
REGISTER_LIMIT = 20
REGISTER_WINDOW_SECONDS = 60 * 60


def enforce_auth_rate_limit(
    db: DBSession,
    request: Request,
    *,
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Apply a shared-database fixed-window limit to an authentication request.

    Only the one-way hash of the scope, client address and identity is persisted.
    Forwarded-IP headers are deliberately not trusted here.
    """
    now = int(time.time())
    window_start = now - (now % window_seconds)
    client_host = request.client.host if request.client else "unknown"
    material = f"{scope}:{client_host}:{identity.strip().lower()}"
    bucket_key = hashlib.sha256(material.encode("utf-8")).hexdigest()

    table = AuthRateLimitBucket.__table__
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        insert = pg_insert
    elif dialect == "sqlite":
        insert = sqlite_insert
    else:
        raise HTTPException(status_code=503, detail="Authentication protection is unavailable")

    try:
        # Prune expired windows; window_start has an index for bounded cleanup.
        expired_keys = (
            select(table.c.bucket_key)
            .where(
                table.c.window_start
                < now - max(REGISTER_WINDOW_SECONDS, LOGIN_WINDOW_SECONDS)
            )
            .limit(500)
        )
        db.execute(delete(table).where(table.c.bucket_key.in_(expired_keys)))
        statement = insert(table).values(
            bucket_key=bucket_key,
            window_start=window_start,
            request_count=1,
        )
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            index_elements=[table.c.bucket_key],
            set_={
                "window_start": excluded.window_start,
                "request_count": case(
                    (table.c.window_start == excluded.window_start, table.c.request_count + 1),
                    else_=1,
                ),
            },
        ).returning(table.c.window_start, table.c.request_count)

        stored_window, request_count = db.execute(statement).one()
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=503, detail="Authentication protection is unavailable")

    if request_count > limit:
        retry_after = max(1, stored_window + window_seconds - now)
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
