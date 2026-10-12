
from fastapi import FastAPI

app = FastAPI(title="CashFlow Sentinel API")


@app.get("/")
def home():
    return {
        "message": "CashFlow Sentinel API is running!",
        "status": "success"
    }
