
from fastapi import FastAPI

app = FastAPI(title="CashFlow Sentinel API")


@app.get("/")
def home():
    return {
        "message": "CashFlow Sentinel API is running!",
        "status": "success"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project": "CashFlow Sentinel"
    }