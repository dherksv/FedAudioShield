# cloud/api_server.py
import os, json, asyncio, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

app = FastAPI(title="Audio Security API")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

clients: list[WebSocket] = []


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        if websocket in clients:
            clients.remove(websocket)


async def redis_to_ws():
    r = aioredis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("audio:events")
    async for msg in pubsub.listen():
        if msg["type"] == "message":
            data = msg["data"].decode()
            dead = []
            for ws in list(clients):
                try:
                    await ws.send_text(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                if ws in clients:
                    clients.remove(ws)


@app.on_event("startup")
async def startup():
    asyncio.create_task(redis_to_ws())


@app.get("/api/events/recent")
async def recent_events(limit: int = 50):
    try:
        from blockchain.blockchain_writer import BlockchainWriter
        bc    = BlockchainWriter()
        count = bc.contract.functions.getEventCount().call()
        start = max(0, count - limit)
        events = []
        for i in range(start, count):
            e = bc.contract.functions.events(i).call()
            events.append({
                "index":       i,
                "timestamp":   e[0],
                "node_id":     e[1],
                "fingerprint": e[2],
                "keyword":     e[3],
                "emotion":     e[4],
                "if_score":    e[5] / 1000.0,
                "alert_level": e[6],
            })
        return {"events": list(reversed(events))}
    except Exception as ex:
        return {"events": [], "error": str(ex)}
