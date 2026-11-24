import json
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, Text, Index, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

url = settings.database_url
connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

Index("ix_messages_session_created", Message.session_id, Message.id)

def init_db():
    Base.metadata.create_all(bind=engine)

def db_dependency():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def history(db, session_id):
    rows = db.scalars(select(Message).where(Message.session_id == session_id).order_by(Message.id)).all()
    return [{"role": r.role, "content": r.content, **({"metadata": json.loads(r.metadata_json)} if r.metadata_json else {})} for r in rows]
