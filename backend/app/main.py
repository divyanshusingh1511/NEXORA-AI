import json
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import select
from .config import settings
from .database import init_db, engine, db_dependency, Message, history
from .llm import ask, ProvidersUnavailable

app = FastAPI(title="Nexora AI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: str | None = None

    @field_validator("session_id", "message")
    @classmethod
    def trim_required(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

@app.get("/health")
def health(db: Session = Depends(db_dependency)):
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    if len(settings.llm_api_keys) < 2:
        raise HTTPException(status_code=503, detail="at least two provider keys must be configured")
    return {"status": "ok", "keys_configured": len(settings.llm_api_keys), "cache_enabled": True}

@app.post("/chat")
def chat(body: ChatRequest, db: Session = Depends(db_dependency), x_simulate_failure: str | None = Header(default=None)):
    prior = history(db, body.session_id)
    messages = [{"role": "system", "content": body.system_prompt or settings.default_system_prompt}]
    messages.extend({"role": m["role"], "content": m["content"]} for m in prior)
    messages.append({"role": "user", "content": body.message})
    try:
        result = ask(messages, x_simulate_failure)
    except ProvidersUnavailable:
        raise HTTPException(status_code=503, detail="all providers unavailable")
    db.add(Message(session_id=body.session_id, role="user", content=body.message))
    db.add(Message(session_id=body.session_id, role="assistant", content=result.reply, metadata_json=json.dumps(result.metadata)))
    db.commit()
    return {"session_id": body.session_id, "reply": result.reply, "metadata": result.metadata}

@app.get("/sessions/{session_id}/messages")
def get_messages(session_id: str, db: Session = Depends(db_dependency)):
    exists = db.scalar(select(Message.id).where(Message.session_id == session_id).limit(1))
    if exists is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "messages": history(db, session_id)}
