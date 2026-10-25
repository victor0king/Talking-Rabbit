"""
database.py
SQLAlchemy engine, session factory, and declarative base.
Every other module gets its DB session through get_db().
"""
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

def _create_engine_with_fallback():
    try:
        eng = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )
        with eng.connect():
            pass
        return eng
    except Exception as exc:
        sqlite_path = settings.BASE_DIR / "storage" / "talking_rabbitt.db"
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(
            f"sqlite:///{sqlite_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

engine = _create_engine_with_fallback()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Call once on startup."""
    import models  # noqa: F401  (ensures models are registered on Base)
    Base.metadata.create_all(bind=engine)

    # Auto-migration for chat_history sessions columns
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            dialect_name = engine.dialect.name
            if dialect_name == "mysql":
                res = conn.execute(text("SHOW COLUMNS FROM chat_history LIKE 'session_id'")).fetchone()
                if not res:
                    conn.execute(text("ALTER TABLE chat_history ADD COLUMN session_id VARCHAR(255) NULL"))
                    conn.execute(text("ALTER TABLE chat_history ADD COLUMN session_title VARCHAR(255) NULL"))
                    conn.execute(text("CREATE INDEX idx_chat_session ON chat_history (session_id)"))
                    conn.execute(text("UPDATE chat_history SET session_id = 'default', session_title = 'Previous Chat' WHERE session_id IS NULL"))
            elif dialect_name == "sqlite":
                columns = [row[1] for row in conn.execute(text("PRAGMA table_info(chat_history)")).fetchall()]
                if "session_id" not in columns:
                    conn.execute(text("ALTER TABLE chat_history ADD COLUMN session_id VARCHAR(255)"))
                if "session_title" not in columns:
                    conn.execute(text("ALTER TABLE chat_history ADD COLUMN session_title VARCHAR(255)"))
    except Exception as e:
        print(f"Database migration note: {e}")
