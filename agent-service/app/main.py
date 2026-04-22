from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="IHRS Agent Service", version="0.0.1")


class ConsultRequest(BaseModel):
    symptom: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "agent-service", "status": "UP"}


@app.post("/consult")
def consult(payload: ConsultRequest) -> dict[str, object]:
    return {
        "symptom": payload.symptom,
        "departmentRecommendation": "全科/内科初诊",
        "doctorRecommendation": [],
        "reason": "当前为骨架阶段，后续将在这里接入大模型导诊与规则筛选逻辑。",
        "disclaimer": "AI 推荐仅供辅助参考，不能替代医生诊断。"
    }
