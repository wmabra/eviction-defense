"""Database initialization."""
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database.models import Base

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _is_duplicate_race(exc: Exception) -> bool:
    """True when an error is the benign concurrent-schema race.

    SQLite DDL (``CREATE TABLE`` / ``ALTER TABLE ... ADD COLUMN``) is not
    atomic across processes. With multiple uvicorn workers a second worker can
    race the first between ``checkfirst`` and the DDL and observe ``table
    already exists`` or ``duplicate column name``. Both mean the other worker
    already made the schema change, so they are safe to ignore.
    """
    msg = str(exc).lower()
    return "already exists" in msg or "duplicate column" in msg


def init_db():
    """Create all tables and apply lightweight column migrations.

    create_all only creates *missing tables* — it does not add new columns to
    existing tables. So we run a small additive migration afterward to backfill
    new columns (state, user_id, progress) onto an existing ``cases`` table.

    Safe to run concurrently from multiple uvicorn workers: ``checkfirst`` and
    the additive migration are not atomic across processes, so a worker that
    loses the startup race gets a benign ``already exists`` / ``duplicate
    column`` error. We swallow that (the other worker already made the change)
    so the losing worker never crashes startup.
    """
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except (OperationalError, ProgrammingError) as exc:
        if not _is_duplicate_race(exc):
            raise
    try:
        _migrate()
    except (OperationalError, ProgrammingError) as exc:
        if not _is_duplicate_race(exc):
            raise


def _migrate():
    """Additive, idempotent migration for columns added after initial deploy.

    Every DDL statement below is a fixed string keyed by an allowlisted column
    name — there is no string interpolation, so there is no injection surface.
    """
    from sqlalchemy import DDL, inspect

    inspector = inspect(engine)
    if "cases" not in inspector.get_table_names():
        return

    existing = {c["name"] for c in inspector.get_columns("cases")}
    is_sqlite = "sqlite" in settings.database_url

    add_column_sqlite = {
        "state": "ALTER TABLE cases ADD COLUMN state VARCHAR",
        "user_id": "ALTER TABLE cases ADD COLUMN user_id VARCHAR",
        "progress": "ALTER TABLE cases ADD COLUMN progress INTEGER DEFAULT 0",
        "intake_data": "ALTER TABLE cases ADD COLUMN intake_data JSON",
    }
    add_column_postgres = {
        "state": "ALTER TABLE cases ADD COLUMN IF NOT EXISTS state VARCHAR",
        "user_id": "ALTER TABLE cases ADD COLUMN IF NOT EXISTS user_id VARCHAR",
        "progress": "ALTER TABLE cases ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0",
        "intake_data": "ALTER TABLE cases ADD COLUMN IF NOT EXISTS intake_data JSON",
    }
    statements = add_column_sqlite if is_sqlite else add_column_postgres

    # The statements above are hardcoded allowlisted constants (no user input),
    # and SQL identifiers cannot be bind-parameterized, so raw DDL is required.
    with engine.begin() as conn:
        for col, stmt in statements.items():
            if col not in existing:
                conn.execute(DDL(stmt))  # pi-lens-ignore: python-sql-injection

        if "ix_cases_user_id" not in {i["name"] for i in inspector.get_indexes("cases")}:
            conn.execute(DDL("CREATE INDEX IF NOT EXISTS ix_cases_user_id ON cases (user_id)"))  # pi-lens-ignore: python-sql-injection


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
