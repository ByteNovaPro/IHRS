from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any

from app.mcp_client import BackendMcpClient, McpClientError


logger = logging.getLogger(__name__)

DEFAULT_DEPARTMENT = "全科/内科初诊"
MAX_HOSPITALS = 8
MAX_ROOMS_PER_HOSPITAL = 2
MAX_DOCTOR_CANDIDATES = 12
DEFAULT_RESULT_LIMIT = 5
SEARCH_HOSPITAL_LIMIT_WITH_LOCATION_HINT = 30
QUERY_KEYWORD_CANDIDATES = (
    "发热",
    "发烧",
    "高热",
    "高烧",
    "咳嗽",
    "咳痰",
    "喘",
    "气短",
    "呼吸困难",
    "胸闷",
    "胸痛",
    "心悸",
    "高血压",
    "胃痛",
    "反酸",
    "腹痛",
    "腹泻",
    "便秘",
    "牙痛",
    "牙龈",
    "口腔",
    "失眠",
    "乏力",
    "儿童",
    "孩子",
    "宝宝",
    "孕",
    "产检",
    "胎动",
    "颈",
    "肩",
    "腰",
    "腿痛",
    "康复",
    "针灸",
)
HOSPITAL_LEVEL_HINTS = {
    "三级甲等": ("三级甲等", "三甲"),
    "三级乙等": ("三级乙等", "三乙"),
    "二级甲等": ("二级甲等", "二甲"),
    "二级乙等": ("二级乙等", "二乙"),
}
DEPARTMENT_MATCH_TOKENS = {
    "心内诊室": ("心内", "心血管", "心脏"),
    "呼吸诊室": ("呼吸", "肺"),
    "消化诊室": ("消化", "胃", "肠"),
    "儿科门诊": ("儿科", "儿童", "小儿"),
    "产科门诊": ("产科", "孕", "妊娠"),
    "口腔专科": ("口腔", "牙"),
    "针灸康复科": ("针灸", "康复", "理疗"),
    "中医内科/治未病门诊": ("中医", "治未病"),
    DEFAULT_DEPARTMENT: ("全科", "内科", "初诊"),
}
DOCTOR_TITLE_SCORES = {
    "主任医师": 3,
    "副主任医师": 2,
    "主治医师": 1,
}
REGION_CITY_ALIASES = {
    "广东": ("广州", "深圳"),
    "广东省": ("广州", "深圳"),
    "浙江": ("杭州", "宁波"),
    "浙江省": ("杭州", "宁波"),
    "江苏": ("南京", "苏州"),
    "江苏省": ("南京", "苏州"),
    "山东": ("济南", "青岛"),
    "山东省": ("济南", "青岛"),
    "福建": ("福州", "厦门"),
    "福建省": ("福州", "厦门"),
    "湖南": ("长沙",),
    "湖南省": ("长沙",),
    "湖北": ("武汉",),
    "湖北省": ("武汉",),
    "河南": ("郑州",),
    "河南省": ("郑州",),
    "安徽": ("合肥",),
    "安徽省": ("合肥",),
    "四川": ("成都",),
    "四川省": ("成都",),
    "陕西": ("西安",),
    "陕西省": ("西安",),
    "上海": ("上海",),
    "北京市": ("北京",),
    "北京": ("北京",),
    "天津": ("天津",),
    "天津市": ("天津",),
    "重庆": ("重庆",),
    "重庆市": ("重庆",),
}
GENERIC_LOCATION_HOSPITAL_TERMS = sorted(
    {
        "".join(str(region or "").strip().lower().split())
        for region in REGION_CITY_ALIASES
    }
    | {
        "".join(str(city or "").strip().lower().split())
        for city_aliases in REGION_CITY_ALIASES.values()
        for city in city_aliases
    }
)


async def recommend_doctors_for_consult(
    *,
    department: str,
    recommendation_query_text: str,
    urgency: str,
    input_category: str,
    auth_header: str | None = None,
    limit: int = DEFAULT_RESULT_LIMIT,
) -> list[dict[str, Any]]:
    if input_category != "medical" or urgency == "emergency":
        return []

    client = BackendMcpClient(auth_header=auth_header)
    try:
        query_text = str(recommendation_query_text or "").strip()
        location_hints = extract_location_hints(query_text)
        hospital_search_level = extract_hospital_search_level(query_text)
        hospital_search_keyword = extract_hospital_search_keyword(query_text)
        hospitals_payload = await client.search_hospitals(
            keyword=hospital_search_keyword,
            city_hint=",".join(location_hints),
            level=hospital_search_level,
            limit=SEARCH_HOSPITAL_LIMIT_WITH_LOCATION_HINT if location_hints else MAX_HOSPITALS,
        )
        hospitals = list(hospitals_payload.get("hospitals", []))
        hospitals = filter_hospitals_by_location_hints(hospitals, location_hints)
        if not hospitals:
            return []

        normalized_query = normalize_text(query_text)
        query_tokens = extract_query_tokens(query_text)
        department_tokens = get_department_tokens(department)

        room_candidates = await collect_room_candidates(
            client=client,
            hospitals=hospitals,
            department=department,
            department_tokens=department_tokens,
            query_tokens=query_tokens,
            normalized_query=normalized_query,
        )
        if not room_candidates:
            return []

        doctor_candidates = await collect_doctor_candidates(
            client=client,
            room_candidates=room_candidates,
            department_tokens=department_tokens,
            query_tokens=query_tokens,
            normalized_query=normalized_query,
        )
        if not doctor_candidates:
            return []

        try:
            quota_map = await fetch_quota_map(
                client=client,
                doctor_ids=[int(item["doctor"]["doctor_id"]) for item in doctor_candidates],
            )
        except McpClientError as exc:
            logger.warning("MCP quota lookup failed, continuing without quota data: %s", exc)
            quota_map = {}

        recommendations: list[dict[str, Any]] = []
        for candidate in doctor_candidates:
            hospital = candidate["hospital"]
            room = candidate["room"]
            doctor = candidate["doctor"]
            quota = quota_map.get(int(doctor["doctor_id"]))
            recommendations.append(
                {
                    "score": candidate["score"],
                    "matchReason": build_match_reason(
                        hospital_name=str(hospital.get("hospital_name", "") or ""),
                        room_name=str(room.get("room_name", "") or ""),
                        specialty=str(doctor.get("specialty", "") or ""),
                        quota=quota,
                    ),
                    "hospital": {
                        "id": hospital.get("hospital_id"),
                        "name": hospital.get("hospital_name"),
                        "level": hospital.get("level"),
                        "location": hospital.get("location"),
                        "shortIntro": hospital.get("short_intro"),
                        "detailIntro": hospital.get("detail_intro"),
                    },
                    "room": {
                        "id": room.get("room_id"),
                        "hospitalId": room.get("hospital_id"),
                        "hospitalName": room.get("hospital_name"),
                        "name": room.get("room_name"),
                        "floor": room.get("floor"),
                        "shortIntro": room.get("short_intro"),
                        "detailIntro": room.get("detail_intro"),
                    },
                    "doctor": {
                        "id": doctor.get("doctor_id"),
                        "hospitalId": doctor.get("hospital_id"),
                        "hospitalName": doctor.get("hospital_name"),
                        "roomId": doctor.get("room_id"),
                        "roomName": doctor.get("room_name"),
                        "name": doctor.get("doctor_name"),
                        "title": doctor.get("title"),
                        "specialty": doctor.get("specialty"),
                        "workTimeSlot": doctor.get("work_time_slot"),
                        "shortIntro": doctor.get("short_intro"),
                        "detailIntro": doctor.get("detail_intro"),
                    },
                    "quota": (
                        {
                            "doctorId": quota.get("doctor_id"),
                            "appointmentDate": quota.get("appointment_date"),
                            "timeSlot": quota.get("time_slot"),
                            "reservedCount": quota.get("reserved_count"),
                            "remainingCount": quota.get("remaining_count"),
                            "capacity": quota.get("capacity"),
                        }
                        if quota
                        else None
                    ),
                }
            )

        recommendations.sort(key=build_recommendation_sort_key)
        return recommendations[: max(1, min(limit, DEFAULT_RESULT_LIMIT))]
    except McpClientError as exc:
        logger.warning("MCP doctor recommendation failed: %s", exc)
        return []
    finally:
        await client.close()


async def collect_room_candidates(
    *,
    client: BackendMcpClient,
    hospitals: list[dict[str, Any]],
    department: str,
    department_tokens: tuple[str, ...],
    query_tokens: list[str],
    normalized_query: str,
) -> list[dict[str, Any]]:
    room_candidates: list[dict[str, Any]] = []
    for hospital in hospitals:
        hospital_id = hospital.get("hospital_id")
        if hospital_id is None:
            continue

        rooms_payload = await client.list_rooms(hospital_id=int(hospital_id))
        rooms = list(rooms_payload.get("rooms", []))
        scored_rooms = []
        for room in rooms:
            score = score_room(
                room=room,
                department=department,
                department_tokens=department_tokens,
                query_tokens=query_tokens,
                normalized_query=normalized_query,
            )
            if score <= 0:
                continue
            scored_rooms.append(
                {
                    "score": score,
                    "hospital": hospital,
                    "room": room,
                }
            )

        scored_rooms.sort(key=lambda item: item["score"], reverse=True)
        room_candidates.extend(scored_rooms[:MAX_ROOMS_PER_HOSPITAL])

    room_candidates.sort(
        key=lambda item: (
            -int(item["score"]),
            str(item["hospital"].get("hospital_name", "") or ""),
            int(item["room"].get("room_id") or 0),
        )
    )
    return room_candidates[: MAX_HOSPITALS * MAX_ROOMS_PER_HOSPITAL]


async def collect_doctor_candidates(
    *,
    client: BackendMcpClient,
    room_candidates: list[dict[str, Any]],
    department_tokens: tuple[str, ...],
    query_tokens: list[str],
    normalized_query: str,
) -> list[dict[str, Any]]:
    doctor_candidates: list[dict[str, Any]] = []
    for room_candidate in room_candidates:
        room = room_candidate["room"]
        hospital = room_candidate["hospital"]
        doctors_payload = await client.list_doctors(
            hospital_id=int(room["hospital_id"]),
            room_id=int(room["room_id"]),
            limit=20,
        )
        doctors = list(doctors_payload.get("doctors", []))
        for doctor in doctors:
            score = score_doctor(
                doctor=doctor,
                room_score=int(room_candidate["score"]),
                department_tokens=department_tokens,
                query_tokens=query_tokens,
                normalized_query=normalized_query,
            )
            if score <= 0:
                continue
            doctor_candidates.append(
                {
                    "score": score,
                    "hospital": hospital,
                    "room": room,
                    "doctor": doctor,
                }
            )

    doctor_candidates.sort(
        key=lambda item: (
            -int(item["score"]),
            str(item["hospital"].get("hospital_name", "") or ""),
            int(item["doctor"].get("doctor_id") or 0),
        )
    )
    return dedupe_doctor_candidates(doctor_candidates)[:MAX_DOCTOR_CANDIDATES]


async def fetch_quota_map(*, client: BackendMcpClient, doctor_ids: list[int]) -> dict[int, dict[str, Any]]:
    unique_doctor_ids = sorted({doctor_id for doctor_id in doctor_ids if doctor_id})
    if not unique_doctor_ids:
        return {}

    start_date = date.today()
    end_date = start_date + timedelta(days=6)
    quota_payload = await client.get_doctor_quota_calendar(
        doctor_ids=unique_doctor_ids,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )
    quota_items = list(quota_payload.get("items", []))
    grouped: dict[int, list[dict[str, Any]]] = {}
    for item in quota_items:
        doctor_id = int(item.get("doctor_id") or 0)
        if doctor_id <= 0:
            continue
        grouped.setdefault(doctor_id, []).append(item)

    quota_map: dict[int, dict[str, Any]] = {}
    for doctor_id, items in grouped.items():
        best_item = choose_best_quota(items)
        if best_item is not None:
            quota_map[doctor_id] = best_item
    return quota_map


def choose_best_quota(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    available_items = [
        item
        for item in items
        if int(item.get("remaining_count") or 0) > 0
    ]
    if not available_items:
        return None

    available_items.sort(
        key=lambda item: (
            str(item.get("appointment_date") or ""),
            -int(item.get("remaining_count") or 0),
            str(item.get("time_slot") or ""),
        )
    )
    return available_items[0]


def build_recommendation_sort_key(item: dict[str, Any]) -> tuple[int, str, int, int]:
    quota = item.get("quota") or {}
    has_quota = 0 if quota else 1
    appointment_date = str(quota.get("appointmentDate") or "9999-12-31")
    remaining_count = -int(quota.get("remainingCount") or 0)
    score = -int(item.get("score") or 0)
    return (has_quota, appointment_date, remaining_count, score)


def extract_location_hints(query_text: str) -> list[str]:
    normalized_query = normalize_text(query_text)
    if not normalized_query:
        return []

    matched_hints: list[str] = []
    for region, city_aliases in REGION_CITY_ALIASES.items():
        if normalize_text(region) not in normalized_query:
            continue
        for city in city_aliases:
            if city not in matched_hints:
                matched_hints.append(city)

    for city in (
        "上海",
        "北京",
        "广州",
        "深圳",
        "杭州",
        "南京",
        "苏州",
        "成都",
        "重庆",
        "武汉",
        "西安",
        "天津",
        "长沙",
        "郑州",
        "青岛",
        "合肥",
        "宁波",
        "厦门",
        "福州",
        "济南",
    ):
        if city in query_text and city not in matched_hints:
            matched_hints.append(city)

    return matched_hints


def extract_hospital_search_level(query_text: str) -> str:
    normalized_query = normalize_text(query_text)
    if not normalized_query:
        return ""

    for canonical_level, aliases in HOSPITAL_LEVEL_HINTS.items():
        if any(normalize_text(alias) in normalized_query for alias in aliases):
            return canonical_level
    return ""


def extract_hospital_search_keyword(query_text: str) -> str:
    text = str(query_text or "").strip()
    if not text:
        return ""

    candidates: list[str] = []
    for pattern in (
        r"([\u4e00-\u9fa5A-Za-z0-9]{2,30}(?:妇幼保健院|中医院|人民医院|儿童医院|院区|医院))",
    ):
        candidates.extend(match.group(1).strip() for match in re.finditer(pattern, text))

    ranked_candidates = sorted(
        {
            clean_hospital_search_keyword_candidate(candidate)
            for candidate in candidates
            if clean_hospital_search_keyword_candidate(candidate)
        },
        key=score_hospital_search_keyword_candidate,
        reverse=True,
    )
    return ranked_candidates[0] if ranked_candidates else ""


def clean_hospital_search_keyword_candidate(candidate: str) -> str:
    text = str(candidate or "").strip()
    while text:
        updated = text
        for prefix in (
            "帮我推荐",
            "帮我找",
            "我想找",
            "我想去",
            "我想要",
            "我要",
            "推荐一下",
            "推荐",
            "最好",
            "帮我",
            "想要",
            "想找",
            "找",
        ):
            if updated.startswith(prefix):
                updated = updated[len(prefix):].strip()
        if updated == text:
            break
        text = updated

    cleaned = text.replace("的", "").strip()
    normalized_cleaned = normalize_text(cleaned)
    if any(normalized_cleaned == f"{location}医院" for location in GENERIC_LOCATION_HOSPITAL_TERMS):
        return ""
    return cleaned


def score_hospital_search_keyword_candidate(candidate: str) -> tuple[int, int, int]:
    text = candidate.strip()
    normalized = normalize_text(text)

    score = 0
    if any(token in text for token in ("人民医院", "中医院", "儿童医院", "妇幼保健院", "院区")):
        score += 4
    if "医院" in text:
        score += 1
    if any(token in normalized for token in ("我想", "帮我", "推荐", "最好", "找", "挂号", "预约")):
        score -= 5
    if any(token in normalized for token in ("三甲", "三级甲等", "二甲", "三级乙等", "医院推荐")):
        score -= 4

    return (score, len(text), -len(normalized))


def filter_hospitals_by_location_hints(
    hospitals: list[dict[str, Any]],
    location_hints: list[str],
) -> list[dict[str, Any]]:
    if not location_hints:
        return hospitals

    filtered = [
        hospital
        for hospital in hospitals
        if hospital_matches_location_hints(hospital, location_hints)
    ]
    return filtered


def hospital_matches_location_hints(hospital: dict[str, Any], location_hints: list[str]) -> bool:
    searchable_text = normalize_text(
        " ".join(
            str(hospital.get(field, "") or "")
            for field in ("hospital_name", "location", "short_intro", "detail_intro")
        )
    )
    if not searchable_text:
        return False
    return any(normalize_text(city_hint) in searchable_text for city_hint in location_hints)


def dedupe_doctor_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_doctor_ids: set[int] = set()
    for item in items:
        doctor_id = int(item["doctor"].get("doctor_id") or 0)
        if doctor_id <= 0 or doctor_id in seen_doctor_ids:
            continue
        deduped.append(item)
        seen_doctor_ids.add(doctor_id)
    return deduped


def score_room(
    *,
    room: dict[str, Any],
    department: str,
    department_tokens: tuple[str, ...],
    query_tokens: list[str],
    normalized_query: str,
) -> int:
    room_text = normalize_text(
        " ".join(
            str(room.get(field, "") or "")
            for field in ("room_name", "hospital_name", "short_intro", "detail_intro", "floor")
        )
    )
    if not room_text:
        return 0

    score = 0
    for token in department_tokens:
        if token and token in room_text:
            score += 8

    for token in query_tokens:
        if token and token in room_text:
            score += 3 if len(token) >= 3 else 2

    if department == DEFAULT_DEPARTMENT:
        if any(token in room_text for token in DEPARTMENT_MATCH_TOKENS[DEFAULT_DEPARTMENT]):
            score += 6
        if any(token in normalized_query for token in ("发热", "发烧", "咳嗽", "咳痰", "喘")) and "呼吸" in room_text:
            score += 6
        if any(token in normalized_query for token in ("腹痛", "反酸", "腹泻", "便秘", "胃痛")) and "消化" in room_text:
            score += 6
        if any(token in normalized_query for token in ("胸闷", "胸痛", "心悸", "高血压")) and ("心内" in room_text or "心血管" in room_text):
            score += 6
        if any(token in normalized_query for token in ("牙痛", "牙龈", "口腔")) and "口腔" in room_text:
            score += 6

    return score


def score_doctor(
    *,
    doctor: dict[str, Any],
    room_score: int,
    department_tokens: tuple[str, ...],
    query_tokens: list[str],
    normalized_query: str,
) -> int:
    searchable_text = normalize_text(
        " ".join(
            str(doctor.get(field, "") or "")
            for field in (
                "hospital_name",
                "room_name",
                "doctor_name",
                "title",
                "specialty",
                "short_intro",
                "detail_intro",
                "work_time_slot",
            )
        )
    )
    if not searchable_text:
        return 0

    score = room_score * 3
    for token in department_tokens:
        if token and token in searchable_text:
            score += 5

    for token in query_tokens:
        if token and token in searchable_text:
            score += 4 if len(token) >= 3 else 2

    if normalized_query and normalized_query in searchable_text:
        score += 4

    title = str(doctor.get("title", "") or "")
    score += DOCTOR_TITLE_SCORES.get(title, 0)
    return score


def extract_query_tokens(query_text: str) -> list[str]:
    raw_tokens = [
        token.strip()
        for token in re.split(r"[，。,.、；;：:\s]+", str(query_text or ""))
        if token.strip()
    ]
    tokens = {
        token
        for token in raw_tokens
        if len(token) >= 2
    }
    normalized_query = normalize_text(query_text)
    for keyword in QUERY_KEYWORD_CANDIDATES:
        if keyword in normalized_query:
            tokens.add(keyword)
    return sorted(tokens, key=lambda token: (-len(token), token))


def get_department_tokens(department: str) -> tuple[str, ...]:
    tokens = list(DEPARTMENT_MATCH_TOKENS.get(department, ()))
    cleaned_department = str(department or "").replace("门诊", "").replace("专科", "").replace("/", "")
    if cleaned_department:
        tokens.append(cleaned_department)
    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = token.strip()
        if not normalized or normalized in seen:
            continue
        deduped.append(normalized)
        seen.add(normalized)
    return tuple(deduped)


def build_match_reason(*, hospital_name: str, room_name: str, specialty: str, quota: dict[str, Any] | None) -> str:
    specialty_text = specialty.strip() or room_name.strip() or "当前分诊方向"
    if quota:
        appointment_date = str(quota.get("appointment_date") or "")
        remaining_count = int(quota.get("remaining_count") or 0)
        return f"{hospital_name} 的 {room_name} 与当前分诊方向较匹配，医生擅长 {specialty_text}，{appointment_date} 还有 {remaining_count} 个可预约号。"
    return f"{hospital_name} 的 {room_name} 与当前分诊方向较匹配，医生擅长 {specialty_text}。"


def normalize_text(value: Any) -> str:
    return "".join(str(value or "").strip().lower().split())
