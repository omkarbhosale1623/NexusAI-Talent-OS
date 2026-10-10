"""Schema-drift guard.

Asserts the schema produced by running the Alembic migrations (001 -> 002) is
identical — at the table and column level — to what the SQLAlchemy models
declare (`Base.metadata`).

This is what prevents the exact drift we found between the models and the older
DB dumps: add a column/table to `models.py` without a matching migration and
this test fails.

Note: the repo's migrations live in a package literally named `alembic`, which
shadows the installed alembic package when tests run from `backend/`. So rather
than use alembic's runtime, we execute each migration's `upgrade()` against a
tiny `op` shim backed by SQLAlchemy Core — the migrations only use
create_table / create_index / add_column / get_bind.
"""
import importlib
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Connection

_VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"
# Applied in dependency order (down_revision chain).
_MIGRATIONS = ["001_initial_schema.py", "002_feature_modules.py"]


class _OpShim:
    """Minimal stand-in for alembic.op backed by a live SQLAlchemy connection."""

    def __init__(self, conn: Connection):
        self.conn = conn
        self.meta = sa.MetaData()

    def get_bind(self) -> Connection:
        return self.conn

    def create_table(self, name, *columns, **kw):
        table = sa.Table(name, self.meta, *columns)
        table.create(self.conn)
        return table

    def create_index(self, index_name, table_name, columns, unique=False, **kw):
        table = self.meta.tables[table_name]
        sa.Index(index_name, *[table.c[c] for c in columns], unique=unique).create(self.conn)

    def add_column(self, table_name, column, **kw):
        coltype = column.type.compile(dialect=self.conn.dialect)
        self.conn.exec_driver_sql(
            f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {coltype}'
        )


def _load_migration(filename: str):
    path = _VERSIONS / filename
    spec = importlib.util.spec_from_file_location(f"_mig_{filename[:3]}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # runs `from alembic import op` -> the shim
    return module


def _columns_by_table(conn: Connection) -> dict[str, set[str]]:
    insp = inspect(conn)
    return {
        t: {c["name"] for c in insp.get_columns(t)}
        for t in insp.get_table_names()
        if t != "alembic_version"
    }


def _schema_from_models() -> dict[str, set[str]]:
    from app.models.models import Base
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        Base.metadata.create_all(conn)
        return _columns_by_table(conn)


def _schema_from_migrations() -> dict[str, set[str]]:
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        alembic_pkg = importlib.import_module("alembic")  # local (shadowing) package
        alembic_pkg.op = _OpShim(conn)  # migrations do `from alembic import op`
        try:
            for filename in _MIGRATIONS:
                _load_migration(filename).upgrade()
            return _columns_by_table(conn)
        finally:
            if hasattr(alembic_pkg, "op"):
                del alembic_pkg.op


def test_migrations_match_models():
    models = _schema_from_models()
    migrated = _schema_from_migrations()

    models_only = set(models) - set(migrated)
    migrations_only = set(migrated) - set(models)
    assert not models_only, f"tables in models but missing from migrations: {sorted(models_only)}"
    assert not migrations_only, f"tables in migrations but not in models: {sorted(migrations_only)}"

    drift = {}
    for table in models:
        missing = models[table] - migrated[table]
        extra = migrated[table] - models[table]
        if missing or extra:
            drift[table] = {"missing_in_migration": sorted(missing),
                            "extra_in_migration": sorted(extra)}
    assert not drift, f"column drift between models and migrations: {drift}"


def test_migrations_cover_feature_module_tables():
    """Explicit guard for the 5 tables/columns the older dumps were missing."""
    migrated = _schema_from_migrations()
    for table in ("coding_submissions", "recruiter_feedback", "ats_connections",
                  "calendar_connections", "outbound_messages"):
        assert table in migrated, f"migration is missing feature table: {table}"
    assert {"fraud_risk_score", "recording_s3_key", "transport"} <= migrated["interviews"]
    assert {"coding_config", "panel_personas"} <= migrated["jobs"]
