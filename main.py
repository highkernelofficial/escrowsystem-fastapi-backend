from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
import uvicorn

app = FastAPI(title="Escrow System API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Welcome to EventKernel FastAPI Backend API"}

@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}

app.include_router(api_router, prefix="/api/v1")

# only for local testing
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# uv run main.py