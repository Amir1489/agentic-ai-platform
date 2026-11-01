import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _alembic_config(database_url):
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    os.environ["DATABASE_URL"] = database_url
    return config


def test_fresh_database_migrates_to_head(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'fresh.db'}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert "auth_rate_limit_buckets" in inspector.get_table_names()
        indexes = {item["name"] for item in inspector.get_indexes("auth_rate_limit_buckets")}
        assert "ix_auth_rate_limit_buckets_window_start" in indexes
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert revision == "0002_auth_rate_limits"
    finally:
        engine.dispose()


def test_existing_rate_limit_table_gets_index_on_upgrade(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'existing.db'}"
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE auth_rate_limit_buckets (
                    bucket_key VARCHAR(64) PRIMARY KEY,
                    window_start INTEGER NOT NULL,
                    request_count INTEGER NOT NULL
                )
            """))
            connection.execute(text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            ))
            connection.execute(text(
                "INSERT INTO alembic_version (version_num) VALUES ('0001_initial')"
            ))
    finally:
        engine.dispose()

    config = _alembic_config(database_url)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        indexes = {item["name"] for item in inspect(engine).get_indexes("auth_rate_limit_buckets")}
        assert "ix_auth_rate_limit_buckets_window_start" in indexes
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == "0002_auth_rate_limits"
    finally:
        engine.dispose()
