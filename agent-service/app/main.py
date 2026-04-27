from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.conversation_store import ConversationStore
from app.doctor_recommendation import recommend_doctors_for_consult
from app.llm import LangChainTriageClient, LlmGenerationError
from app.rag import KnowledgeBase, RetrievedKnowledge


logger = logging.getLogger(__name__)

app = FastAPI(title="IHRS Agent Service", version="0.1.0")
knowledge_base = KnowledgeBase(
    knowledge_dir=Path(__file__).resolve().parent.parent / "knowledge",
    persist_dir=Path(__file__).resolve().parent.parent / "chroma_db",
)
llm_client = LangChainTriageClient()
conversation_store = ConversationStore()

DISCLAIMER = "AI 推荐仅供辅助参考，不能替代医生诊断。"
DEFAULT_DEPARTMENT = "全科/内科初诊"
DEFAULT_REASON = "当前症状信息还不够明确，建议先选择全科或内科初诊，由医生进一步判断是否需要转入专科。"
KNOWN_DEPARTMENTS = (
    "心内诊室",
    "呼吸诊室",
    "消化诊室",
    "儿科门诊",
    "产科门诊",
    "口腔专科",
    "针灸康复科",
    "中医内科/治未病门诊",
    DEFAULT_DEPARTMENT,
)
DEPARTMENT_ALIASES = {
    "心内诊室": ("心内", "心脏", "心血管", "冠心病", "高血压", "心律"),
    "呼吸诊室": ("呼吸", "肺", "咳嗽", "咳痰", "哮喘", "气短"),
    "消化诊室": ("消化", "胃", "肠", "反酸", "腹痛", "腹泻", "便秘"),
    "儿科门诊": ("儿科", "儿童", "孩子", "宝宝", "婴儿"),
    "产科门诊": ("产科", "孕", "妊娠", "胎动", "产检"),
    "口腔专科": ("口腔", "牙", "牙龈", "龋齿", "正畸"),
    "针灸康复科": ("康复", "针灸", "颈肩腰腿", "扭伤", "肩周", "腰椎"),
    "中医内科/治未病门诊": ("中医", "治未病", "调理", "体质", "乏力", "失眠"),
    DEFAULT_DEPARTMENT: ("全科", "内科", "初诊"),
}
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
DEFAULT_FOLLOW_UP_QUESTIONS = [
    "症状持续多久了，是突然出现还是逐渐加重？",
    "有没有发热、剧烈疼痛、呼吸困难、呕吐、出血等伴随情况？",
    "之前是否有类似发作、既往病史，或者正在服用相关药物？",
]
GENERIC_GREETING_FOLLOW_UP_QUESTIONS = [
    "您这次最想咨询的是哪种不舒服，比如疼痛、发热、咳嗽、胃肠不适，还是挂号流程问题？",
    "如果是身体不适，可以直接告诉我最主要的症状和持续多久了。",
    "如果方便，也可以补充年龄、是否在孕期或是否为儿童就诊，这样我能分诊得更准。",
]
NON_MEDICAL_GUIDANCE_FOLLOW_UP_QUESTIONS = [
    "请先告诉我您这次最主要的不舒服是什么，比如疼痛、发热、咳嗽、腹痛、牙痛等。",
    "如果希望我帮您推荐医生，也请一起补充症状持续多久、是否加重，以及想挂哪个方向的门诊。",
    "如果您想问的是挂号流程、医院或医生安排，也可以直接说明具体问题。",
]
DOCTOR_RECOMMENDATION_BUTTON_TEXT = "推荐医生"
DEPARTMENT_FOLLOW_UP_QUESTIONS = {
    "心内诊室": [
        "胸闷或胸痛是活动后更明显，还是安静时也会出现？",
        "是否伴随心悸、呼吸困难、大汗、头晕或血压明显波动？",
        "以前是否有高血压、冠心病或心律失常病史？",
    ],
    "呼吸诊室": [
        "咳嗽有多久了，是否伴发热、咳痰、喘息或夜间加重？",
        "有没有既往哮喘、过敏、慢阻肺或近期呼吸道感染接触史？",
        "气短是在活动后明显，还是静息时也会觉得喘不过气？",
    ],
    "消化诊室": [
        "腹痛或反酸和进食有什么关系，是饭前、饭后还是夜间更明显？",
        "是否伴恶心、呕吐、腹泻、便秘、黑便或体重下降？",
        "以前有没有胃病、肠炎、幽门螺杆菌或相关检查结果？",
    ],
    "儿科门诊": [
        "孩子现在多大了，症状持续多久，精神状态和食欲怎么样？",
        "有没有发热、咳嗽、腹泻、皮疹或夜间哭闹明显增多？",
        "近期是否上幼儿园、接触过生病的小朋友，或者有过敏史？",
    ],
    "产科门诊": [
        "目前孕周大约多少，最近一次产检是什么时候？",
        "有没有腹痛、阴道流血、胎动减少、血压异常或水肿？",
        "这是首次出现不适，还是最近几天持续反复发生？",
    ],
    "口腔专科": [
        "牙痛是冷热刺激痛、咬合痛，还是持续跳痛？",
        "有没有牙龈肿胀、出血、口腔溃疡或张口受限？",
        "最近是否做过补牙、拔牙，或者长期有牙周问题？",
    ],
    "针灸康复科": [
        "疼痛是在扭伤、久坐、运动后出现，还是逐渐加重的？",
        "疼痛会不会放射到手臂或腿部，是否影响走路、睡觉或活动？",
        "之前有没有做过影像检查、理疗，或者有旧伤复发情况？",
    ],
    "中医内科/治未病门诊": [
        "失眠、乏力或不适持续多久了，最近压力和作息怎么样？",
        "有没有食欲差、怕冷、头痛、焦虑或月经变化等伴随情况？",
        "之前是否接受过中医调理，或者长期有慢病需要一起考虑？",
    ],
    DEFAULT_DEPARTMENT: DEFAULT_FOLLOW_UP_QUESTIONS,
}
EMERGENCY_KEYWORDS = (
    "剧烈胸痛",
    "明显呼吸困难",
    "呼吸困难",
    "意识异常",
    "昏厥",
    "晕厥",
    "大汗",
    "抽搐",
    "呕血",
    "黑便",
    "便血",
    "突发无力",
    "突发言语不清",
    "偏瘫",
)
SOON_KEYWORDS = (
    "胸闷",
    "胸痛",
    "气短",
    "心悸",
    "胎动异常",
    "腹痛",
    "反复",
    "加重",
)
FEVER_SOON_KEYWORDS = (
    "持续高热",
    "反复发热",
    "高热",
    "发热不退",
    "持续发烧",
    "反复发烧",
    "高烧",
)
FEVER_WITH_RESPIRATORY_KEYWORDS = (
    "咳嗽",
    "咳痰",
    "喘",
    "气短",
    "呼吸困难",
    "胸闷",
)
CONSULT_STREAM_CHUNK_SIZE = 38
GENERIC_GREETING_PATTERNS = (
    "你好",
    "您好",
    "hello",
    "hi",
    "在吗",
    "有人吗",
    "咨询",
    "咨询一下",
    "问一下",
    "想问一下",
    "帮我看看",
    "医生你好",
)
DOCTOR_RECOMMENDATION_PATTERNS = (
    "推荐医生",
    "医生推荐",
    "帮我推荐医生",
    "推荐可预约",
    "可预约医生",
    "挂哪个医生",
    "适合哪个医生",
    "帮我找医生",
    "帮我选医生",
)
SYMPTOM_KEYWORDS = (
    "痛",
    "胀",
    "酸",
    "麻",
    "晕",
    "闷",
    "咳",
    "喘",
    "烧",
    "吐",
    "泻",
    "血",
    "肿",
    "痒",
    "发热",
    "胸",
    "胃",
    "腹",
    "牙",
    "腰",
    "颈",
    "肩",
    "腿",
    "失眠",
    "乏力",
    "心悸",
    "反酸",
    "便秘",
    "腹泻",
    "症状",
    "不舒服",
    "难受",
)
RULE_MATCH_WEIGHTS = {
    "心内诊室": 4,
    "呼吸诊室": 3,
    "消化诊室": 3,
    "儿科门诊": 5,
    "产科门诊": 5,
    "口腔专科": 4,
    "针灸康复科": 3,
    "中医内科/治未病门诊": 2,
}


class ConsultRequest(BaseModel):
    symptom: str = Field(..., min_length=1, max_length=1000)
    conversationId: Optional[str] = Field(default=None, max_length=128)


class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "service": "agent-service",
        "status": "UP",
        "llmStatus": "ENABLED" if llm_client.is_configured else "DISABLED",
    }


@app.get("/rag/stats")
def rag_stats() -> dict[str, object]:
    collection = knowledge_base.collection
    return {
        "collection": collection.name,
        "count": collection.count(),
        "embeddingVersion": knowledge_base.current_embedding_version,
        "persistDirectory": str(knowledge_base.persist_dir),
        "knowledgeDirectory": str(knowledge_base.knowledge_dir),
    }


@app.get("/rag/documents")
def rag_documents(limit: int = 20) -> dict[str, object]:
    data = knowledge_base.collection.get(limit=limit)
    return {
        "ids": data.get("ids", []),
        "documents": data.get("documents", []),
        "metadatas": data.get("metadatas", []),
        "count": len(data.get("ids", [])),
    }


@app.post("/rag/search")
def rag_search(payload: RagSearchRequest) -> dict[str, object]:
    hits = knowledge_base.search(payload.query, top_k=payload.top_k)
    return {
        "query": payload.query,
        "topK": payload.top_k,
        "results": [
            {
                "id": item.id,
                "text": item.text,
                "metadata": item.metadata,
                "distance": item.distance,
                "score": item.score,
                "source": item.source,
                "matchedTokens": list(item.matched_tokens),
            }
            for item in hits
        ],
    }


@app.post("/consult")
async def consult(payload: ConsultRequest, request: Request) -> dict[str, object]:
    symptom = payload.symptom.strip()
    user_key = extract_consult_user_key(request)
    provided_conversation_id = normalize_conversation_id(payload.conversationId)
    cached_conversation_id = None if provided_conversation_id else await conversation_store.get_user_conversation_id(user_key)
    conversation_id = provided_conversation_id or cached_conversation_id or conversation_store.new_conversation_id()
    if provided_conversation_id:
        await conversation_store.bind_user_conversation(user_key, conversation_id)
    elif cached_conversation_id:
        await conversation_store.bind_user_conversation(user_key, conversation_id)
    else:
        await conversation_store.start_new_conversation_for_user(user_key, conversation_id)
    history = await conversation_store.get_history(conversation_id)
    contextual_symptom = build_contextual_symptom(symptom, history)
    knowledge_hits = knowledge_base.search(contextual_symptom, top_k=4)
    is_generic_greeting = is_generic_greeting_input(symptom)
    is_doctor_recommendation_request = has_doctor_recommendation_intent(symptom)
    is_medical_related_input = is_medical_or_booking_related_input(symptom)
    input_category = determine_input_category(symptom, history)
    fallback_department, fallback_reason = infer_department_and_reason(contextual_symptom, knowledge_hits)
    fallback_urgency = infer_urgency(contextual_symptom, fallback_reason)
    fallback_response = build_consult_response(
        conversation_id=conversation_id,
        symptom=symptom,
        recommendation_query_text=contextual_symptom,
        department=fallback_department,
        reason=fallback_reason,
        generated_answer=build_fallback_answer(
            fallback_department,
            fallback_reason,
            fallback_urgency,
            symptom,
            history=history,
        ),
        follow_up_questions=build_follow_up_questions(fallback_department, symptom, history=history),
        urgency=fallback_urgency,
        answer_mode="fallback",
        knowledge_hits=knowledge_hits,
        patient_summary=build_patient_summary(symptom, input_category=input_category, history=history),
        input_category=input_category,
    )
    response = await resolve_consult_response(
        symptom=symptom,
        contextual_symptom=contextual_symptom,
        history=history,
        knowledge_hits=knowledge_hits,
        fallback_response=fallback_response,
        is_generic_greeting=is_generic_greeting,
        is_doctor_recommendation_request=is_doctor_recommendation_request,
        is_medical_related_input=is_medical_related_input,
        input_category=input_category,
        auth_header=extract_authorization_header(request),
    )
    await persist_consult_exchange(conversation_id, symptom, response)
    return response


@app.post("/consult/stream")
async def consult_stream(payload: ConsultRequest, request: Request) -> StreamingResponse:
    symptom = payload.symptom.strip()
    user_key = extract_consult_user_key(request)
    provided_conversation_id = normalize_conversation_id(payload.conversationId)
    cached_conversation_id = None if provided_conversation_id else await conversation_store.get_user_conversation_id(user_key)
    conversation_id = provided_conversation_id or cached_conversation_id or conversation_store.new_conversation_id()
    if provided_conversation_id:
        await conversation_store.bind_user_conversation(user_key, conversation_id)
    elif cached_conversation_id:
        await conversation_store.bind_user_conversation(user_key, conversation_id)
    else:
        await conversation_store.start_new_conversation_for_user(user_key, conversation_id)
    history = await conversation_store.get_history(conversation_id)
    contextual_symptom = build_contextual_symptom(symptom, history)
    knowledge_hits = knowledge_base.search(contextual_symptom, top_k=4)
    is_generic_greeting = is_generic_greeting_input(symptom)
    is_doctor_recommendation_request = has_doctor_recommendation_intent(symptom)
    is_medical_related_input = is_medical_or_booking_related_input(symptom)
    input_category = determine_input_category(symptom, history)
    fallback_department, fallback_reason = infer_department_and_reason(contextual_symptom, knowledge_hits)
    fallback_urgency = infer_urgency(contextual_symptom, fallback_reason)
    fallback_response = build_consult_response(
        conversation_id=conversation_id,
        symptom=symptom,
        recommendation_query_text=contextual_symptom,
        department=fallback_department,
        reason=fallback_reason,
        generated_answer=build_fallback_answer(
            fallback_department,
            fallback_reason,
            fallback_urgency,
            symptom,
            history=history,
        ),
        follow_up_questions=build_follow_up_questions(fallback_department, symptom, history=history),
        urgency=fallback_urgency,
        answer_mode="fallback",
        knowledge_hits=knowledge_hits,
        patient_summary=build_patient_summary(symptom, input_category=input_category, history=history),
        input_category=input_category,
    )
    initial_response = {
        **fallback_response,
        "departmentRecommendation": "问诊分析中",
        "reason": "正在结合你的描述、知识库和大模型生成问诊建议，请稍等。",
        "generatedAnswer": "",
        "followUpQuestions": [],
        "urgency": "",
        "answerMode": "streaming",
    }

    async def event_generator():
        yield format_sse_event("meta", initial_response)
        response = await resolve_consult_response(
            symptom=symptom,
            contextual_symptom=contextual_symptom,
            history=history,
            knowledge_hits=knowledge_hits,
            fallback_response=fallback_response,
            is_generic_greeting=is_generic_greeting,
            is_doctor_recommendation_request=is_doctor_recommendation_request,
            is_medical_related_input=is_medical_related_input,
            input_category=input_category,
            auth_header=extract_authorization_header(request),
        )

        preview_response = {
            **response,
            "generatedAnswer": "",
            "answerMode": "streaming",
        }
        yield format_sse_event("meta", preview_response)

        for chunk in split_text_for_streaming(str(response.get("generatedAnswer", ""))):
            yield format_sse_event("delta", {"text": chunk})

        await persist_consult_exchange(conversation_id, symptom, response)
        yield format_sse_event("complete", response)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.delete("/consult/conversations/{conversation_id}", status_code=204)
async def delete_consult_conversation(conversation_id: str, request: Request) -> Response:
    normalized_conversation_id = normalize_conversation_id(conversation_id)
    await conversation_store.delete_conversation(normalized_conversation_id)
    await conversation_store.clear_user_conversation_if_matches(
        extract_consult_user_key(request),
        normalized_conversation_id,
    )
    return Response(status_code=204)


@app.get("/consult/session")
async def get_consult_session(request: Request) -> dict[str, object]:
    user_key = extract_consult_user_key(request)
    conversation_id = await conversation_store.get_user_conversation_id(user_key)
    if not conversation_id:
        return {
            "conversationId": None,
            "history": [],
        }

    return {
        "conversationId": conversation_id,
        "history": await conversation_store.get_history(conversation_id),
    }


def build_system_prompt() -> str:
    return (
        "你是 IHRS 智能导诊助手，用中文回答。\n"
        "你的任务是基于患者当前描述、历史对话和知识库片段，给出首诊科室建议，而不是做确定诊断。\n"
        "回答目标是帮助用户挂对首诊科室，不能把自己说成医生，也不能编造化验、影像、体征或确诊结论。\n"
        "如果存在急症红旗，要明确建议立即急诊；如果信息不足，要承认不确定，并给出 2 到 3 个高价值追问。\n"
        "优先复用系统提供的标准科室名称；如果无法确定专科，请回退到全科/内科初诊。\n"
        "输出必须是一个 JSON 对象，不要输出 Markdown、不要输出额外解释。"
    )


def build_user_prompt(
    symptom: str,
    knowledge_hits: list[RetrievedKnowledge],
    fallback_department: str,
    fallback_reason: str,
    history: list[dict[str, str]],
) -> str:
    return (
        f"{build_history_context(history)}\n\n"
        f"患者描述：\n{symptom}\n\n"
        f"规则兜底建议：\n- 推荐科室：{fallback_department}\n- 理由：{fallback_reason}\n\n"
        f"知识库片段：\n{build_knowledge_context(knowledge_hits)}\n\n"
        "请综合判断后，只输出如下 JSON 对象：\n"
        "{\n"
        '  "patientSummary": "一句话概括患者当前描述，不超过 40 个汉字",\n'
        '  "departmentRecommendation": "字符串",\n'
        '  "reason": "一句话说明，尽量控制在 50 个汉字内，直接说分诊依据",\n'
        '  "generatedAnswer": "3 到 4 句中文。先明确推荐科室，再解释依据，再说明需要补充什么信息；如有急症风险要单独提醒。",\n'
        '  "followUpQuestions": ["问题1", "问题2", "问题3"],\n'
        '  "urgency": "normal 或 soon 或 emergency"\n'
        "}\n\n"
        "要求：\n"
        f"- departmentRecommendation 优先使用以下门诊名称之一：{', '.join(KNOWN_DEPARTMENTS)}。\n"
        "- 若知识库与规则建议一致，优先保持一致；若不一致，只有在患者描述出现更明确证据时才改判。\n"
        "- 若知识库不足，可参考规则兜底建议，但不要编造检查结果、诊断或治疗承诺。\n"
        "- generatedAnswer 不要空话，不要只重复“建议就医”，要体现具体依据和下一步补充信息。\n"
        "- followUpQuestions 给 2 到 3 个最有价值且彼此不重复的追问。\n"
        "- 不要输出 JSON 之外的任何内容。"
    )


def infer_department_and_reason(symptom: str, knowledge_hits: list[RetrievedKnowledge]) -> tuple[str, str]:
    if is_generic_greeting_input(symptom):
        return (
            DEFAULT_DEPARTMENT,
            "当前还没有提供具体症状，我可以先根据你接下来补充的不适表现帮你判断挂号方向。",
        )

    if needs_symptom_details(symptom):
        return (
            DEFAULT_DEPARTMENT,
            "当前还缺少明确的症状细节，建议先补充主要不适、持续时间和是否加重，再进一步判断医院和科室。",
        )

    if not is_medical_or_booking_related_input(symptom):
        return (
            DEFAULT_DEPARTMENT,
            "当前这句话还看不出具体症状或挂号需求，建议先补充身体不适或是否需要推荐医生。",
        )

    rule_department, rule_reason, rule_score = infer_department_from_rules(symptom)
    if rule_department:
        if rule_score >= 5 or not knowledge_hits:
            return rule_department, rule_reason

    if knowledge_hits:
        top_hit = knowledge_hits[0]
        department = normalize_department(top_hit.metadata.get("department"), DEFAULT_DEPARTMENT)
        reason = clean_short_text(first_sentence(top_hit.text)) or DEFAULT_REASON
        if department != DEFAULT_DEPARTMENT and not should_rule_override_knowledge(rule_department, department, rule_score):
            return department, reason

    if rule_department:
        return rule_department, rule_reason

    if knowledge_hits:
        top_hit = knowledge_hits[0]
        department = normalize_department(top_hit.metadata.get("department"), DEFAULT_DEPARTMENT)
        reason = clean_short_text(first_sentence(top_hit.text)) or DEFAULT_REASON
        return department, reason

    return (
        DEFAULT_DEPARTMENT,
        DEFAULT_REASON,
    )


def infer_department_from_rules(symptom: str) -> tuple[str | None, str, int]:
    normalized_symptom = symptom.lower()
    best_department: str | None = None
    best_reason = DEFAULT_REASON
    best_score = 0

    for keywords, department, reason in DEPARTMENT_RULES:
        matched_keywords = [keyword for keyword in keywords if keyword.lower() in normalized_symptom]
        if not matched_keywords:
            continue

        score = len(matched_keywords) * RULE_MATCH_WEIGHTS.get(department, 1)
        if department in {"儿科门诊", "产科门诊"}:
            score += 3
        if department == "口腔专科" and any(token in normalized_symptom for token in ("牙痛", "牙龈", "口腔")):
            score += 2
        if department == "心内诊室" and any(token in normalized_symptom for token in ("胸痛", "心悸", "活动后气短")):
            score += 2

        if score > best_score:
            best_department = department
            best_reason = reason
            best_score = score

    return best_department, best_reason, best_score


def should_rule_override_knowledge(rule_department: str | None, knowledge_department: str, rule_score: int) -> bool:
    if not rule_department:
        return False
    if rule_department == knowledge_department:
        return True
    if rule_department in {"儿科门诊", "产科门诊"} and rule_score >= 5:
        return True
    return rule_score >= 8


async def resolve_consult_response(
    *,
    symptom: str,
    contextual_symptom: str,
    history: list[dict[str, str]],
    knowledge_hits: list[RetrievedKnowledge],
    fallback_response: dict[str, object],
    is_generic_greeting: bool = False,
    is_doctor_recommendation_request: bool = False,
    is_medical_related_input: bool = True,
    input_category: str = "medical",
    auth_header: str | None = None,
) -> dict[str, object]:
    if not llm_client.is_configured:
        return await enrich_consult_response_with_doctor_recommendations(fallback_response, auth_header=auth_header)

    try:
        llm_result = await llm_client.generate_json(
            system_prompt=build_system_prompt(),
            user_prompt=build_user_prompt(
                contextual_symptom,
                knowledge_hits,
                str(fallback_response["departmentRecommendation"]),
                str(fallback_response["reason"]),
                history,
            ),
        )
    except LlmGenerationError as exc:
        logger.warning("LLM consult generation failed, falling back to local triage: %s", exc)
        return await enrich_consult_response_with_doctor_recommendations(fallback_response, auth_header=auth_header)

    fallback_department = str(fallback_response["departmentRecommendation"])
    fallback_reason = str(fallback_response["reason"])
    patient_summary = normalize_patient_summary(
        llm_result.get("patientSummary"),
        symptom,
        input_category=input_category,
        history=history,
    )
    department = normalize_department(llm_result.get("departmentRecommendation"), fallback_department)
    reason = normalize_reason(llm_result.get("reason"), fallback_reason)
    follow_up_questions = sanitize_follow_up_questions(llm_result.get("followUpQuestions")) or build_follow_up_questions(
        department,
        symptom,
        history=history,
    )
    urgency = normalize_urgency(llm_result.get("urgency"), infer_urgency(contextual_symptom, f"{reason} {fallback_reason}"))
    generated_answer = finalize_generated_answer(
        llm_result.get("generatedAnswer"),
        department=department,
        reason=reason,
        urgency=urgency,
        follow_up_questions=follow_up_questions,
    )

    response = build_consult_response(
        conversation_id=str(fallback_response["conversationId"]),
        symptom=symptom,
        recommendation_query_text=contextual_symptom,
        department=department,
        reason=reason,
        generated_answer=generated_answer,
        follow_up_questions=follow_up_questions,
        urgency=urgency,
        answer_mode="langchain",
        knowledge_hits=knowledge_hits,
        patient_summary=patient_summary,
        input_category=input_category,
    )
    return await enrich_consult_response_with_doctor_recommendations(response, auth_header=auth_header)


async def enrich_consult_response_with_doctor_recommendations(
    response: dict[str, object],
    *,
    auth_header: str | None = None,
) -> dict[str, object]:
    if not bool(response.get("showDoctorRecommendationAction")):
        return response

    recommendations = await recommend_doctors_for_consult(
        department=str(response.get("departmentRecommendation", "") or ""),
        recommendation_query_text=str(response.get("recommendationQueryText", "") or ""),
        urgency=str(response.get("urgency", "") or ""),
        input_category=str(response.get("inputCategory", "") or ""),
        auth_header=auth_header,
    )
    if not recommendations:
        return response

    return {
        **response,
        "doctorRecommendation": recommendations,
        "doctorRecommendationPrompt": "如果你希望系统继续结合当前分诊结果查看可预约医生，可以点击下方“推荐医生”。",
    }


def build_consult_response(
    *,
    conversation_id: str,
    symptom: str,
    recommendation_query_text: str,
    department: str,
    reason: str,
    generated_answer: str,
    follow_up_questions: list[str],
    urgency: str,
    answer_mode: str,
    knowledge_hits: list[RetrievedKnowledge],
    patient_summary: str,
    input_category: str,
) -> dict[str, object]:
    show_doctor_recommendation_action = should_show_doctor_recommendation_action(
        input_category=input_category,
        department=department,
        urgency=urgency,
    )
    return {
        "conversationId": conversation_id,
        "symptom": symptom,
        "recommendationQueryText": recommendation_query_text,
        "patientSummary": patient_summary,
        "inputCategory": input_category,
        "departmentRecommendation": department,
        "doctorRecommendation": [],
        "reason": reason,
        "generatedAnswer": generated_answer,
        "followUpQuestions": follow_up_questions,
        "urgency": urgency,
        "showDoctorRecommendationAction": show_doctor_recommendation_action,
        "doctorRecommendationButtonText": DOCTOR_RECOMMENDATION_BUTTON_TEXT if show_doctor_recommendation_action else "",
        "doctorRecommendationPrompt": build_doctor_recommendation_prompt(show_doctor_recommendation_action),
        "answerMode": answer_mode,
        "disclaimer": DISCLAIMER,
        "knowledgeReferences": build_knowledge_references(knowledge_hits),
    }


def build_fallback_answer(
    department: str,
    reason: str,
    urgency: str,
    symptom: str = "",
    *,
    history: list[dict[str, str]] | None = None,
) -> str:
    if is_generic_greeting_input(symptom):
        if has_medical_context_in_history(history or []):
            return (
                f"我会结合你前面的症状继续分析，当前建议先挂 {department}。"
                f"{ensure_sentence(reason)}"
                "如果你现在想继续挂号或推荐医生，也可以直接说明，我会基于前文继续判断。"
            )
        return (
            "你好，我可以帮你判断应该挂哪个科，也可以根据症状帮你梳理是否需要尽快就医。"
            "你可以直接告诉我这次最主要的不舒服是什么、持续多久了，或者如果只是想咨询挂号流程，也可以直接说你的问题。"
        )

    if needs_symptom_details(symptom) and not has_medical_context_in_history(history or []):
        return (
            "我已经收到你的问题，但目前还缺少具体症状细节，暂时不能准确推荐医院、诊室和医生。"
            "请补充最主要的不舒服是什么、持续多久了、有没有加重，以及是否伴随发热、疼痛、咳嗽、气短、腹痛、牙痛等表现。"
        )

    if not is_medical_or_booking_related_input(symptom):
        return (
            "我目前还看不出您是在描述症状，还是希望系统帮您推荐医生或解答挂号问题。"
            "您可以直接告诉我最主要的不舒服是什么、持续多久了；如果希望我帮您推荐 1 到 5 位可预约医生，也请明确说明“帮我推荐医生”，并补充症状和就诊诉求。"
        )

    follow_up_summary = summarize_follow_up_questions(build_follow_up_questions(department, symptom, history=history))
    parts = [
        f"根据目前描述，建议先挂 {department}。",
        ensure_sentence(reason),
        build_urgency_sentence(urgency),
    ]
    if follow_up_summary:
        parts.append(f"为了更准确分诊，建议再补充：{follow_up_summary}。")
    return "".join(part for part in parts if part)


def build_follow_up_questions(
    department: str,
    symptom: str = "",
    *,
    history: list[dict[str, str]] | None = None,
) -> list[str]:
    if is_generic_greeting_input(symptom):
        if has_medical_context_in_history(history or []):
            return DEPARTMENT_FOLLOW_UP_QUESTIONS.get(department, DEFAULT_FOLLOW_UP_QUESTIONS)
        return GENERIC_GREETING_FOLLOW_UP_QUESTIONS
    if needs_symptom_details(symptom) and not has_medical_context_in_history(history or []):
        return NON_MEDICAL_GUIDANCE_FOLLOW_UP_QUESTIONS
    if not is_medical_or_booking_related_input(symptom):
        return NON_MEDICAL_GUIDANCE_FOLLOW_UP_QUESTIONS
    return DEPARTMENT_FOLLOW_UP_QUESTIONS.get(department, DEFAULT_FOLLOW_UP_QUESTIONS)


def is_generic_greeting_input(symptom: str) -> bool:
    normalized = normalize_free_text(symptom)
    if not normalized:
        return True

    if len(normalized) <= 6 and normalized in GENERIC_GREETING_PATTERNS:
        return True

    return normalized in GENERIC_GREETING_PATTERNS


def has_doctor_recommendation_intent(symptom: str) -> bool:
    normalized = normalize_free_text(symptom)
    return any(pattern in normalized for pattern in DOCTOR_RECOMMENDATION_PATTERNS)


def has_concrete_symptom_content(symptom: str) -> bool:
    normalized = normalize_free_text(symptom)
    if not normalized:
        return False

    if any(keyword in normalized for keyword in SYMPTOM_KEYWORDS):
        return True

    return any(keyword in normalized for keyword in EMERGENCY_KEYWORDS + SOON_KEYWORDS)


def needs_symptom_details(symptom: str) -> bool:
    normalized = normalize_free_text(symptom)
    if not normalized or is_generic_greeting_input(symptom):
        return False

    if has_concrete_symptom_content(symptom):
        return False

    return any(keyword in normalized for keyword in ("挂号", "预约", "门诊", "科室", "就诊", "医生", "医院", "推荐"))


def is_medical_or_booking_related_input(symptom: str) -> bool:
    normalized = normalize_free_text(symptom)
    if not normalized:
        return False
    if is_generic_greeting_input(symptom):
        return True
    if has_doctor_recommendation_intent(symptom):
        return True
    if any(keyword in normalized for keyword in SYMPTOM_KEYWORDS):
        return True
    if any(keyword in normalized for keyword in ("挂号", "预约", "门诊", "科室", "就诊", "医生", "医院")):
        return True
    return False


def build_knowledge_context(knowledge_hits: list[RetrievedKnowledge]) -> str:
    if not knowledge_hits:
        return "暂无命中的知识库片段。"

    lines: list[str] = []
    for index, item in enumerate(knowledge_hits, start=1):
        metadata = item.metadata or {}
        department = metadata.get("department") or "未标注科室"
        doc_type = metadata.get("type") or "knowledge"
        tags = metadata.get("tags") or "无"
        intent_type = metadata.get("intent_type") or "general"
        urgency_level = metadata.get("urgency_level") or "normal"
        audience = metadata.get("audience") or "general"
        lines.append(
            f"{index}. 科室={department}；类型={doc_type}；意图={intent_type}；紧急度={urgency_level}；适用人群={audience}；标签={tags}；来源={item.source}；分数={item.score:.2f}；内容={clean_long_text(item.text)}"
        )
    return "\n".join(lines)


def build_history_context(history: list[dict[str, str]]) -> str:
    if not history:
        return "历史对话：暂无。"

    lines = ["历史对话："]
    for item in history[-8:]:
        role = "患者" if item.get("role") == "user" else "导诊助手"
        lines.append(f"- {role}：{clean_long_text(item.get('content', ''), limit=240)}")
    return "\n".join(lines)


def build_knowledge_references(knowledge_hits: list[RetrievedKnowledge]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "type": item.metadata.get("type"),
            "department": item.metadata.get("department"),
            "distance": item.distance,
            "score": item.score,
            "source": item.source,
            "matchedTokens": list(item.matched_tokens),
            "intentType": item.metadata.get("intent_type"),
            "urgencyLevel": item.metadata.get("urgency_level"),
            "audience": item.metadata.get("audience"),
        }
        for item in knowledge_hits
    ]


def has_medical_context_in_history(history: list[dict[str, str]]) -> bool:
    if not history:
        return False

    for item in reversed(history[-8:]):
        content = str(item.get("content", "")).strip()
        if not content:
            continue

        if item.get("role") == "user" and (
            has_concrete_symptom_content(content) or is_medical_or_booking_related_input(content)
        ):
            return True

        if item.get("role") == "assistant" and any(department in content for department in KNOWN_DEPARTMENTS):
            return True

    return False


def build_contextual_symptom(symptom: str, history: list[dict[str, str]]) -> str:
    if has_concrete_symptom_content(symptom):
        return symptom

    if not has_medical_context_in_history(history):
        return symptom

    recent_user_contexts: list[str] = []
    for item in reversed(history[-8:]):
        if item.get("role") != "user":
            continue
        content = clean_long_text(item.get("content", ""), limit=120)
        if not content:
            continue
        if has_concrete_symptom_content(content) or is_medical_or_booking_related_input(content):
            recent_user_contexts.append(content)
        if len(recent_user_contexts) >= 2:
            break

    recent_user_contexts.reverse()
    if not recent_user_contexts:
        return symptom

    return f"{'；'.join(recent_user_contexts)}；当前补充诉求：{symptom}"


def determine_input_category(symptom: str, history: list[dict[str, str]] | None = None) -> str:
    has_history_context = has_medical_context_in_history(history or [])

    if is_generic_greeting_input(symptom):
        if has_history_context:
            return "medical"
        return "greeting"
    if needs_symptom_details(symptom):
        if has_history_context:
            return "medical"
        return "symptom_needed"
    if not is_medical_or_booking_related_input(symptom):
        if has_history_context:
            return "medical"
        return "non_medical"
    return "medical"


def build_patient_summary(symptom: str, *, input_category: str, history: list[dict[str, str]] | None = None) -> str:
    cleaned_symptom = clean_long_text(symptom, limit=80)
    if input_category == "greeting":
        return "你目前还没有描述具体症状，主要是在发起本次问诊。"
    if input_category == "symptom_needed":
        return "你提到了就诊或推荐医生需求，但还没有说明明确的病症细节。"
    if input_category == "non_medical":
        return "你当前这句话还不是明确的看病症状描述。"
    if history and not has_concrete_symptom_content(symptom) and has_medical_context_in_history(history):
        return f"你这轮主要是在承接前面的病情继续咨询：{cleaned_symptom or '补充挂号或就诊诉求'}。"
    if not cleaned_symptom:
        return "你目前还没有描述具体症状。"
    return f"你提到的主要情况是：{cleaned_symptom}。"


def normalize_patient_summary(
    candidate: Any,
    symptom: str,
    *,
    input_category: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    summary = clean_short_text(candidate, limit=60)
    if not summary:
        return build_patient_summary(symptom, input_category=input_category, history=history)

    if not summary.endswith(("。", "！", "？")):
        summary = f"{summary}。"

    return summary


def should_show_doctor_recommendation_action(*, input_category: str, department: str, urgency: str) -> bool:
    if input_category != "medical":
        return False
    if urgency == "emergency":
        return False
    return True


def build_doctor_recommendation_prompt(show_action: bool) -> str:
    if not show_action:
        return ""
    return "如果你希望系统继续结合当前分诊结果筛选可预约医生，可以点击下方“推荐医生”。"


def normalize_department(candidate: Any, fallback: str) -> str:
    cleaned = clean_short_text(candidate)
    if not cleaned:
        return fallback

    for department in KNOWN_DEPARTMENTS:
        if cleaned == department:
            return department

    for department, aliases in DEPARTMENT_ALIASES.items():
        if any(alias in cleaned for alias in aliases):
            return department

    return fallback


def normalize_reason(candidate: Any, fallback: str) -> str:
    reason = clean_short_text(candidate)
    if not reason:
        return fallback

    generic_fragments = ("建议就医", "请及时就医", "需要进一步检查", "建议进一步检查", "根据描述建议")
    if any(fragment == reason or reason.startswith(fragment) for fragment in generic_fragments):
        return fallback

    return reason


def normalize_urgency(candidate: Any, fallback: str) -> str:
    cleaned = clean_short_text(candidate).lower()
    if cleaned in {"normal", "soon", "emergency"}:
        return cleaned
    return fallback


def sanitize_follow_up_questions(candidate: Any) -> list[str]:
    if not isinstance(candidate, list):
        return []

    normalized_questions: list[str] = []
    seen: set[str] = set()

    for item in candidate:
        question = clean_short_text(item)
        if not question:
            continue
        if question in seen:
            continue
        normalized_questions.append(question)
        seen.add(question)
        if len(normalized_questions) >= 3:
            break

    return normalized_questions


def finalize_generated_answer(
    candidate: Any,
    *,
    department: str,
    reason: str,
    urgency: str,
    follow_up_questions: list[str],
) -> str:
    generated_answer = clean_long_text(candidate, limit=1200).strip()
    if not is_usable_generated_answer(generated_answer, department):
        return build_structured_answer(department, reason, urgency, follow_up_questions)

    if follow_up_questions:
        summary = summarize_follow_up_questions(follow_up_questions)
        if summary and "补充" not in generated_answer and "还需要" not in generated_answer:
            generated_answer = f"{generated_answer} 为了更准确分诊，建议再补充：{summary}。"

    return clean_long_text(generated_answer, limit=1200)


def is_usable_generated_answer(answer: str, department: str) -> bool:
    if not answer or len(answer) < 28:
        return False
    if "{" in answer or "}" in answer or '"departmentRecommendation"' in answer:
        return False
    if department not in answer and "建议先挂" not in answer and "建议挂" not in answer:
        return False
    return True


def build_structured_answer(
    department: str,
    reason: str,
    urgency: str,
    follow_up_questions: list[str],
) -> str:
    urgency_sentence = build_urgency_sentence(urgency)
    follow_up_summary = summarize_follow_up_questions(follow_up_questions)
    parts = [
        f"根据目前描述，建议先挂 {department}。",
        ensure_sentence(reason),
        urgency_sentence,
    ]
    if follow_up_summary:
        parts.append(f"为了更准确分诊，建议再补充：{follow_up_summary}。")
    return clean_long_text("".join(part for part in parts if part).strip(), limit=1200)


def build_urgency_sentence(urgency: str) -> str:
    if urgency == "emergency":
        return "如果此刻伴随剧烈胸痛、明显呼吸困难、意识异常、抽搐或呕血黑便等情况，请立即前往急诊。"
    if urgency == "soon":
        return "如果症状正在加重、反复发作，或者已经明显影响进食、睡眠或活动，建议尽快到院面诊。"
    return "如果症状持续存在、近期反复，或者逐渐加重，也建议尽快安排门诊面诊。"


def summarize_follow_up_questions(follow_up_questions: list[str]) -> str:
    normalized = [question.rstrip("？?。") for question in follow_up_questions if question]
    if not normalized:
        return ""
    return "；".join(normalized[:2])


def infer_urgency(symptom: str, reason: str) -> str:
    if is_generic_greeting_input(symptom):
        return "normal"

    combined_text = f"{symptom} {reason}"
    if any(keyword in combined_text for keyword in EMERGENCY_KEYWORDS):
        return "emergency"
    if infer_fever_related_urgency(combined_text) == "soon":
        return "soon"
    if any(keyword in combined_text for keyword in SOON_KEYWORDS):
        return "soon"
    return "normal"


def infer_fever_related_urgency(text: str) -> str:
    normalized = normalize_free_text(text)
    if not normalized:
        return "normal"

    has_fever = any(token in normalized for token in ("发热", "发烧", "高热", "高烧"))
    if not has_fever:
        return "normal"

    if any(keyword in normalized for keyword in FEVER_SOON_KEYWORDS):
        return "soon"

    if any(keyword in normalized for keyword in ("38.5", "39", "39.0", "39度", "39℃", "40度", "40℃")):
        return "soon"

    has_duration_or_recurrence = any(keyword in normalized for keyword in ("持续", "反复", "不退", "几天", "多天"))
    has_respiratory_risk = any(keyword in normalized for keyword in FEVER_WITH_RESPIRATORY_KEYWORDS)
    if has_duration_or_recurrence and has_respiratory_risk:
        return "soon"

    return "normal"


def first_sentence(text: str) -> str:
    cleaned = clean_long_text(text)
    if not cleaned:
        return ""

    for separator in ("。", "！", "？"):
        if separator in cleaned:
            head, _ = cleaned.split(separator, 1)
            return f"{head.strip()}{separator}"
    return cleaned


def clean_short_text(value: Any, limit: int = 120) -> str:
    cleaned = " ".join(str(value or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


def clean_long_text(value: Any, limit: int = 400) -> str:
    cleaned = " ".join(str(value or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."


def normalize_free_text(value: Any) -> str:
    return "".join(str(value or "").strip().lower().split())


def ensure_sentence(text: str) -> str:
    cleaned = clean_short_text(text)
    if not cleaned:
        return ""
    if cleaned.endswith(("。", "！", "？")):
        return cleaned
    return f"{cleaned}。"


def format_sse_event(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def split_text_for_streaming(text: str) -> list[str]:
    normalized = clean_long_text(text, limit=1200).strip()
    if not normalized:
        return []

    sentence_chunks: list[str] = []
    buffer = ""
    for char in normalized:
        buffer += char
        if char in {"。", "！", "？", "；"}:
            sentence_chunks.append(buffer)
            buffer = ""
    if buffer:
        sentence_chunks.append(buffer)

    chunks: list[str] = []
    for sentence in sentence_chunks:
        if len(sentence) <= CONSULT_STREAM_CHUNK_SIZE:
            chunks.append(sentence)
            continue

        start = 0
        while start < len(sentence):
            chunks.append(sentence[start : start + CONSULT_STREAM_CHUNK_SIZE])
            start += CONSULT_STREAM_CHUNK_SIZE

    return [chunk for chunk in chunks if chunk]


def normalize_conversation_id(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def extract_consult_user_key(request: Request) -> str | None:
    header_value = request.headers.get("X-Consult-User-Key")
    normalized = str(header_value or "").strip()
    return normalized or None


def extract_authorization_header(request: Request) -> str | None:
    header_value = request.headers.get("Authorization")
    normalized = str(header_value or "").strip()
    return normalized or None


async def persist_consult_exchange(conversation_id: str, symptom: str, response: dict[str, Any]) -> None:
    assistant_message = clean_long_text(
        "\n".join(
            [
                f"推荐科室：{response.get('departmentRecommendation', '')}",
                str(response.get("reason", "")).strip(),
                str(response.get("generatedAnswer", "")).strip(),
            ]
        ),
        limit=1200,
    )
    await conversation_store.append_messages(
        conversation_id,
        [
            {"role": "user", "content": symptom},
            {"role": "assistant", "content": assistant_message},
        ],
    )
