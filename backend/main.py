import os
import sys

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from init_db import seed
from routers import (
    accounts,
    auth,
    dashboard,
    meetings,
    opportunities,
    pipeline,
    proposals,
    risk,
    users,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()
    yield


app = FastAPI(title="AI Sales Assistant API", version="1.0.0", lifespan=lifespan)

# 로컬 개발 서버 + Vercel에 배포된 프론트엔드(매 배포마다 서브도메인이 바뀔 수 있어 정규식으로 허용) 모두 허용.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5177"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(opportunities.router)
app.include_router(risk.router)
app.include_router(pipeline.router)
app.include_router(meetings.router)
app.include_router(proposals.router)
app.include_router(dashboard.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
