# Entry point — run with: uvicorn main:app --reload
from app.main import app  # noqa: F401

@app.get("/health")
def health():
    return {"status":"ok", "service":"aws-networking"}
    # return {"status": "ok"}
