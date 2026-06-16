import os
import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from customer_service import run_customer_service

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Redis 连接（不可用时自动降级为内存存储）
REDIS_PREFIX = "crewai_cs:"
HISTORY_TTL = 3600
_memory_store: dict[str, list[dict]] = {}

try:
    import redis
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True, socket_connect_timeout=2)
    r.ping()
    USE_REDIS = True
    print(f"[server] Redis 已连接: {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    USE_REDIS = False
    r = None
    print(f"[server] Redis 不可用({e})，使用内存存储")


def get_history(session_id: str) -> list[dict]:
    if USE_REDIS:
        data = r.get(f"{REDIS_PREFIX}{session_id}")
        return json.loads(data) if data else []
    return _memory_store.get(session_id, [])


def save_history(session_id: str, history: list[dict]):
    if USE_REDIS:
        r.set(f"{REDIS_PREFIX}{session_id}", json.dumps(history, ensure_ascii=False), ex=HISTORY_TTL)
    else:
        _memory_store[session_id] = history


def clear_history_store(session_id: str):
    if USE_REDIS:
        r.delete(f"{REDIS_PREFIX}{session_id}")
    else:
        _memory_store.pop(session_id, None)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    history = get_history(req.session_id)

    # 构建历史上下文（全部对话）
    history_text = ""
    if history:
        lines = []
        for h in history:
            lines.append(f"客户: {h['user']}")
            lines.append(f"客服: {h['bot']}")
        history_text = "\n".join(lines)

    reply = await asyncio.to_thread(run_customer_service, req.message, history_text)

    history.append({"user": req.message, "bot": str(reply)})
    save_history(req.session_id, history)

    return ChatResponse(reply=str(reply))


@app.post("/api/clear")
async def clear(req: ChatRequest):
    clear_history_store(req.session_id)
    return {"message": "历史已清空"}
