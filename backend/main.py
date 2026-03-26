import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from fastapi.staticfiles import StaticFiles
from routes import alert, alerts, cameras, health, stream, responder

app = FastAPI(title="SafeSight Backend")

# ── Static Files (for snapshots) ─────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── CORS (fully open for cross-origin dashboard + detector access) ──────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(alert.router)
app.include_router(stream.router)
app.include_router(cameras.router)
app.include_router(health.router)
app.include_router(alerts.router)
app.include_router(responder.router)

# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
