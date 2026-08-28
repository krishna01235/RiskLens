from fastapi import FastAPI

app = FastAPI(
    title="RiskLens API",
    version="0.1.0",
    description="Event-driven quantitative risk monitoring platform.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
