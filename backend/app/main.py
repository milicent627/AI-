from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import story, chapter, continuation, world_book, foreshadowing, model_config, summary

app = FastAPI(title="BookWright - AI小说写作与续写器", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(story.router)
app.include_router(chapter.router)
app.include_router(continuation.router)
app.include_router(world_book.router)
app.include_router(foreshadowing.router)
app.include_router(model_config.router)
app.include_router(summary.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
