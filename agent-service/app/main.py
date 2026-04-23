from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="IHRS Agent Service", version="0.0.1")


class ConsultRequest(BaseModel):
    symptom: str


DEPARTMENT_RULES = [
    (("胸闷", "胸痛", "心悸", "高血压", "心律", "气短"), "心内诊室", "症状中出现胸闷、胸痛、心悸或血压相关描述，建议优先进行心血管方向评估。"),
    (("咳嗽", "咳痰", "发热", "哮喘", "喘", "肺炎", "呼吸"), "呼吸诊室", "症状集中在咳嗽、发热、喘息或呼吸不适，建议优先选择呼吸系统相关门诊。"),
    (("胃痛", "反酸", "烧心", "腹胀", "腹泻", "便秘", "胃", "肠"), "消化诊室", "症状涉及胃肠不适、反酸烧心或排便异常，建议优先选择消化方向门诊。"),
    (("儿童", "孩子", "小孩", "宝宝", "婴儿", "幼儿"), "儿科门诊", "描述中出现儿童或婴幼儿就诊场景，建议优先选择儿科相关门诊。"),
    (("孕", "产检", "胎动", "妊娠", "产前"), "产科门诊", "症状或诉求与孕期、产检、胎动或围产管理相关，建议优先选择产科门诊。"),
    (("牙", "口腔", "牙痛", "龋齿", "正畸", "牙龈"), "口腔专科", "症状集中在牙齿、牙龈、正畸或口腔检查，建议优先选择口腔专科。"),
    (("失眠", "乏力", "调理", "亚健康", "体质"), "中医内科/治未病门诊", "诉求偏慢性调理、睡眠、乏力或亚健康管理，可考虑中医内科或治未病门诊。"),
    (("颈", "肩", "腰", "腿痛", "康复", "扭伤"), "针灸康复科", "症状涉及颈肩腰腿痛、运动损伤或康复需求，可考虑针灸康复科。"),
]


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "agent-service", "status": "UP"}


@app.post("/consult")
def consult(payload: ConsultRequest) -> dict[str, object]:
    symptom = payload.symptom.strip()
    normalized_symptom = symptom.lower()
    department = "全科/内科初诊"
    reason = "当前症状信息还不够明确，建议先选择全科或内科初诊，由医生进一步判断是否需要转入专科。"

    for keywords, matched_department, matched_reason in DEPARTMENT_RULES:
        if any(keyword.lower() in normalized_symptom for keyword in keywords):
            department = matched_department
            reason = matched_reason
            break

    return {
        "symptom": symptom,
        "departmentRecommendation": department,
        "doctorRecommendation": [],
        "reason": reason,
        "disclaimer": "AI 推荐仅供辅助参考，不能替代医生诊断。"
    }
