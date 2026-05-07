from fastapi import FastAPI

from app.routers import auth, certificates, contracts, daily_entries, suppliers

app = FastAPI(title="DFT Mass Balance API", version="0.1.0")

app.include_router(auth.router)
app.include_router(suppliers.router)
app.include_router(contracts.router)
app.include_router(certificates.router)
app.include_router(daily_entries.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
