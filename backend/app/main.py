from fastapi import FastAPI

from app.routers import auth

app = FastAPI(title="DFT Mass Balance API", version="0.2.0")

app.include_router(auth.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}
