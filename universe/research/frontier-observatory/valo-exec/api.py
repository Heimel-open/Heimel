from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from engine import evaluate

app = FastAPI(title="Valo Exec", version="0.1.0")


class AgentRequest(BaseModel):
    agent: str
    intent: str
    target: str
    amount_risk: Optional[str] = "low"
    critical_service: Optional[bool] = False
    authority_level: Optional[str] = "sufficient"
    uncertainty: Optional[str] = None


@app.post("/evaluate")
def evaluate_request(request: AgentRequest):
    return evaluate(request.model_dump())


@app.get("/health")
def health():
    return {"status": "ok", "service": "valo_exec"}
