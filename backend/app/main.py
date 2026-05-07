from fastapi import FastAPI

app = FastAPI(title="DFT Mass Balance API", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
