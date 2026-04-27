from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{1,4}|[a-zA-Z0-9]+")
DEFAULT_FASTEMBED_MODEL = os.getenv("RAG_EMBEDDING_MODEL_NAME", "BAAI/bge-small-zh-v1.5").strip()
DEFAULT_FASTEMBED_DEVICE = os.getenv("RAG_EMBEDDING_DEVICE", "cpu").strip().lower() or "cpu"
DEFAULT_FASTEMBED_CACHE_DIR = os.getenv("RAG_EMBEDDING_CACHE_DIR", "").strip() or None
FALLBACK_EMBEDDING_VERSION = "stable-hash-v1"
COLLECTION_PREFIX = "ihrs_knowledge_"

logger = logging.getLogger(__name__)

DEPARTMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "全科/内科初诊": ("全科", "内科", "初诊", "普通内科", "综合内科"),
    "呼吸诊室": ("呼吸", "肺", "呼吸科", "咳嗽", "气喘"),
    "心内诊室": ("心内", "心血管", "胸痛", "心悸", "高血压"),
    "消化诊室": ("消化", "胃肠", "胃痛", "腹痛", "腹泻"),
    "口腔专科": ("口腔", "牙科", "牙痛", "牙龈", "龋齿"),
    "儿科门诊": ("儿科", "儿童", "小儿", "宝宝", "婴儿"),
    "产科门诊": ("产科", "孕", "妊娠", "胎动", "产检"),
    "针灸康复科": ("康复", "针灸", "理疗", "腰腿痛", "运动损伤"),
    "中医内科/治未病门诊": ("中医", "调理", "治未病", "失眠", "乏力"),
}

FOLLOW_UP_HINTS = ("多久", "几天", "多长时间", "持续", "最高", "多少度", "是否", "伴有", "还有", "加重")
RECOMMENDATION_HINTS = ("挂号", "预约", "推荐医生", "推荐医院", "推荐科室", "医生推荐")
CHILD_HINTS = ("儿童", "孩子", "小孩", "宝宝", "婴儿", "幼儿")
PREGNANT_HINTS = ("怀孕", "孕", "妊娠", "胎动", "产检", "孕周", "破水")
URGENT_HINTS = ("剧烈", "持续高热", "高热", "呼吸困难", "意识异常", "抽搐", "呕血", "黑便", "破水", "大出血")
SOON_HINTS = ("加重", "反复", "持续", "高烧", "39", "40", "精神差", "脱水", "胸闷", "气短")
INTENT_SIGNAL_ALIASES: dict[str, tuple[str, ...]] = {
    "symptom_match": ("看什么科", "什么科", "哪个科", "什么门诊", "症状"),
    "follow_up": ("多久", "几天", "是否伴有", "还有什么", "体温多少", "持续多久"),
    "red_flag": ("危险吗", "严重吗", "要不要急诊", "急诊", "危险信号"),
    "recommendation_request": ("推荐医生", "推荐医院", "挂号", "预约", "医生推荐"),
}
AUDIENCE_ALIASES: dict[str, tuple[str, ...]] = {
    "children": CHILD_HINTS,
    "pregnant": PREGNANT_HINTS,
    "general": (),
}


@dataclass(frozen=True)
class RetrievedKnowledge:
    id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None
    score: float = 0.0
    source: str = "semantic"
    matched_tokens: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryProfile:
    intent_preferences: tuple[str, ...]
    audiences: tuple[str, ...]
    urgency_preferences: tuple[str, ...]
    recommendation_requested: bool = False
    emergency_like: bool = False
    department_hints: tuple[str, ...] = ()


class HashEmbeddingFunction(EmbeddingFunction[Documents]):
    """A lightweight deterministic embedding fallback suitable for small demo corpora."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed(text) for text in input]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall(text.lower())

        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            token_hash = int.from_bytes(digest[:8], byteorder="big", signed=False)
            index = token_hash % self.dimensions
            sign = 1.0 if digest[8] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]


class FastEmbedEmbeddingFunction(EmbeddingFunction[Documents]):
    """FastEmbed-based embedding backend for lightweight Chinese semantic retrieval."""

    def __init__(self, model_name: str, device: str = "cpu", cache_dir: str | None = None) -> None:
        from fastembed import TextEmbedding

        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        providers = ["CPUExecutionProvider"]
        if device in {"cuda", "gpu"}:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

        init_kwargs: dict[str, Any] = {
            "model_name": model_name,
            "providers": providers,
        }
        if cache_dir:
            init_kwargs["cache_dir"] = cache_dir

        self._model = TextEmbedding(**init_kwargs)

    def __call__(self, input: Documents) -> Embeddings:
        vectors = self._model.embed(list(input))
        return [vector.tolist() for vector in vectors]


class KnowledgeBase:
    def __init__(self, knowledge_dir: Path, persist_dir: Path) -> None:
        self.knowledge_dir = knowledge_dir
        self.persist_dir = persist_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._documents = self._load_documents()
        self.embedding_version, self.embedding_function = build_embedding_backend()
        self.collection_name = f"{COLLECTION_PREFIX}{sanitize_collection_suffix(self.embedding_version)}"

        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._rebuild_collection()

    def search(self, query: str, top_k: int = 5, where: dict[str, Any] | None = None) -> list[RetrievedKnowledge]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        query_tokens = self._tokenize(normalized_query)
        query_profile = self._infer_query_profile(normalized_query, query_tokens)
        candidate_count = max(top_k * 3, 8)
        result = self._collection.query(
            query_texts=[normalized_query],
            n_results=candidate_count,
            where=where,
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        semantic_hits = [
            RetrievedKnowledge(
                id=item_id,
                text=document,
                metadata=metadata or {},
                distance=distance,
                source="semantic",
            )
            for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances)
        ]

        lexical_hits = self._build_lexical_shortlist(
            query=normalized_query,
            query_tokens=query_tokens,
            query_profile=query_profile,
            top_k=max(top_k * 2, 6),
            where=where,
            exclude_ids={item.id for item in semantic_hits},
        )
        return self._rerank_hits(normalized_query, query_tokens, query_profile, semantic_hits + lexical_hits)[:top_k]

    @property
    def collection(self) -> Collection:
        return self._collection

    @property
    def current_embedding_version(self) -> str:
        return self.embedding_version

    def _rebuild_collection(self) -> None:
        self._drop_existing_knowledge_collections()
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={
                "description": "IHRS triage and hospital knowledge base",
                "embedding_version": self.embedding_version,
            },
        )

        docs = self._documents
        if not docs:
            return

        self._collection.upsert(
            ids=[item["id"] for item in docs],
            documents=[item["text"] for item in docs],
            metadatas=[item["metadata"] for item in docs],
        )

    def _drop_existing_knowledge_collections(self) -> None:
        for collection in self._client.list_collections():
            collection_name = getattr(collection, "name", None) or str(collection)
            if not collection_name.startswith(COLLECTION_PREFIX):
                continue
            self._client.delete_collection(name=collection_name)

    def _load_documents(self) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for path in sorted(self.knowledge_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            records = payload if isinstance(payload, list) else [payload]
            for item in records:
                docs.append(
                    {
                        "id": item["id"],
                        "text": item["text"].strip(),
                        "metadata": item.get("metadata", {}),
                    }
                )
        return docs

    def _rerank_hits(
        self,
        query: str,
        query_tokens: list[str],
        query_profile: QueryProfile,
        hits: list[RetrievedKnowledge],
    ) -> list[RetrievedKnowledge]:
        deduped_hits: dict[str, RetrievedKnowledge] = {}
        for item in hits:
            deduped_hits.setdefault(item.id, item)

        scored = [
            self._score_hit(query, query_tokens, query_profile, hit)
            for hit in deduped_hits.values()
        ]
        scored.sort(
            key=lambda item: (
                item[0],
                -(item[1].distance if item[1].distance is not None else 9999.0),
                item[1].id,
            ),
            reverse=True,
        )
        return [item for score, item in scored if score > 0]

    def _score_hit(
        self,
        query: str,
        query_tokens: list[str],
        query_profile: QueryProfile,
        hit: RetrievedKnowledge,
    ) -> tuple[float, RetrievedKnowledge]:
        metadata = hit.metadata or {}
        department = str(metadata.get("department", "")).strip().lower()
        tags = self._extract_metadata_tags(metadata)
        department_aliases = self._extract_department_aliases(metadata)
        scene_tags = self._extract_metadata_terms(metadata, "scene_tags", "intent_signals")
        searchable_text = " ".join([hit.text, department, " ".join(tags), " ".join(department_aliases), " ".join(scene_tags)]).lower()
        priority = float(metadata.get("priority", 0) or 0)

        overlap_score = 0.0
        matched_tokens: list[str] = []
        for token in query_tokens:
            if token in tags:
                overlap_score += 5.0
                matched_tokens.append(token)
            elif token in department_aliases:
                overlap_score += 4.5
                matched_tokens.append(token)
            elif token in scene_tags:
                overlap_score += 3.5
                matched_tokens.append(token)
            elif token in department:
                overlap_score += 4.0
                matched_tokens.append(token)
            elif token in searchable_text:
                overlap_score += 2.0
                matched_tokens.append(token)

        if department and department in query.lower():
            overlap_score += 6.0
        for hint in query_profile.department_hints:
            if hint and hint in department_aliases:
                overlap_score += 4.0
        overlap_score += self._profile_boost(query_profile, metadata)
        if query.lower() and query.lower() in hit.text.lower():
            overlap_score += 4.0

        distance_score = 0.0
        if hit.distance is not None:
            distance_score = max(0.0, 3.5 - float(hit.distance))

        final_score = overlap_score + distance_score + priority * 0.2
        return (
            final_score,
            RetrievedKnowledge(
                id=hit.id,
                text=hit.text,
                metadata=hit.metadata,
                distance=hit.distance,
                score=final_score,
                source=hit.source,
                matched_tokens=tuple(sorted(set(matched_tokens), key=matched_tokens.index)),
            ),
        )

    def _build_lexical_shortlist(
        self,
        *,
        query: str,
        query_tokens: list[str],
        query_profile: QueryProfile,
        top_k: int,
        where: dict[str, Any] | None,
        exclude_ids: set[str],
    ) -> list[RetrievedKnowledge]:
        scored: list[tuple[float, dict[str, Any]]] = []
        normalized_query = query.lower()
        for document in self._documents:
            item_id = str(document["id"])
            if item_id in exclude_ids:
                continue
            metadata = document.get("metadata", {})
            if not self._metadata_matches_where(metadata, where):
                continue

            department_aliases = self._extract_department_aliases(metadata)
            scene_tags = self._extract_metadata_terms(metadata, "scene_tags", "intent_signals")
            searchable_text = " ".join(
                [
                    document["text"],
                    str(metadata.get("department", "") or ""),
                    " ".join(self._extract_metadata_tags(metadata)),
                    " ".join(department_aliases),
                    " ".join(scene_tags),
                ]
            ).lower()
            lexical_score = 0.0
            for token in query_tokens:
                if token and token in searchable_text:
                    lexical_score += 3.0 if len(token) >= 2 else 1.0
            if normalized_query and normalized_query in searchable_text:
                lexical_score += 4.0
            lexical_score += self._profile_boost(query_profile, metadata)
            lexical_score += float(metadata.get("priority", 0) or 0) * 0.2
            if lexical_score <= 0:
                continue
            scored.append((lexical_score, document))

        scored.sort(key=lambda item: (item[0], item[1]["id"]), reverse=True)
        return [
            RetrievedKnowledge(
                id=item["id"],
                text=item["text"],
                metadata=item.get("metadata", {}),
                distance=None,
                source="lexical",
            )
            for _, item in scored[:top_k]
        ]

    def _extract_metadata_tags(self, metadata: dict[str, Any]) -> list[str]:
        raw_values = [metadata.get("tags", ""), metadata.get("symptom_tags", "")]
        return self._normalize_term_list(raw_values)

    def _extract_department_aliases(self, metadata: dict[str, Any]) -> list[str]:
        department = str(metadata.get("department", "") or "").strip()
        raw_values = [metadata.get("department_aliases", "")]
        if department:
            raw_values.append(",".join(DEPARTMENT_ALIASES.get(department, ())))
        return self._normalize_term_list(raw_values)

    def _extract_metadata_terms(self, metadata: dict[str, Any], *keys: str) -> list[str]:
        raw_values = [metadata.get(key, "") for key in keys]
        intent_type = str(metadata.get("intent_type", "") or "").strip().lower()
        audience = str(metadata.get("audience", "") or "").strip().lower()
        if intent_type:
            raw_values.append(",".join(INTENT_SIGNAL_ALIASES.get(intent_type, ())))
        if audience:
            raw_values.append(",".join(AUDIENCE_ALIASES.get(audience, ())))
        return self._normalize_term_list(raw_values)

    def _normalize_term_list(self, raw_values: list[Any]) -> list[str]:
        tags: list[str] = []
        for raw in raw_values:
            for tag in str(raw).split(","):
                normalized = tag.strip().lower()
                if normalized and normalized not in tags:
                    tags.append(normalized)
        return tags

    def _infer_query_profile(self, query: str, query_tokens: list[str]) -> QueryProfile:
        normalized_query = query.lower()
        recommendation_requested = any(hint in normalized_query for hint in RECOMMENDATION_HINTS)
        follow_up_like = any(hint in normalized_query for hint in FOLLOW_UP_HINTS)
        emergency_like = any(hint in normalized_query for hint in URGENT_HINTS)
        soon_like = emergency_like or any(hint in normalized_query for hint in SOON_HINTS)

        audiences: list[str] = ["general"]
        if any(hint in normalized_query for hint in CHILD_HINTS):
            audiences.insert(0, "children")
        if any(hint in normalized_query for hint in PREGNANT_HINTS):
            audiences.insert(0, "pregnant")

        if emergency_like:
            intent_preferences = ("red_flag", "symptom_match", "follow_up")
        elif recommendation_requested and not follow_up_like:
            intent_preferences = ("recommendation_request", "symptom_match", "follow_up")
        elif follow_up_like:
            intent_preferences = ("follow_up", "symptom_match", "red_flag")
        else:
            intent_preferences = ("symptom_match", "follow_up", "red_flag")

        if emergency_like:
            urgency_preferences = ("emergency", "soon")
        elif soon_like:
            urgency_preferences = ("soon", "normal")
        else:
            urgency_preferences = ("normal", "soon")

        department_hints: list[str] = []
        for aliases in DEPARTMENT_ALIASES.values():
            for alias in aliases:
                if alias.lower() in normalized_query and alias.lower() not in department_hints:
                    department_hints.append(alias.lower())

        return QueryProfile(
            intent_preferences=intent_preferences,
            audiences=tuple(audiences),
            urgency_preferences=urgency_preferences,
            recommendation_requested=recommendation_requested,
            emergency_like=emergency_like,
            department_hints=tuple(department_hints),
        )

    def _profile_boost(self, query_profile: QueryProfile, metadata: dict[str, Any]) -> float:
        score = 0.0
        intent_type = str(metadata.get("intent_type", "") or "").strip().lower()
        audience = str(metadata.get("audience", "") or "").strip().lower()
        urgency_level = str(metadata.get("urgency_level", "") or "").strip().lower()

        for index, preferred_intent in enumerate(query_profile.intent_preferences):
            if preferred_intent == intent_type:
                score += max(1.5, 4.5 - index * 1.5)
                break

        for index, preferred_audience in enumerate(query_profile.audiences):
            if preferred_audience == audience:
                score += max(1.0, 4.0 - index)
                break

        primary_audience = query_profile.audiences[0] if query_profile.audiences else "general"
        if primary_audience in {"children", "pregnant"} and audience not in {primary_audience, ""}:
            score -= 3.0 if audience == "general" else 1.5

        for index, preferred_urgency in enumerate(query_profile.urgency_preferences):
            if preferred_urgency == urgency_level:
                score += max(0.5, 2.5 - index)
                break

        if intent_type == "red_flag" and not query_profile.emergency_like:
            score -= 1.0
        if intent_type == "recommendation_request" and query_profile.recommendation_requested:
            score += 3.5
        return score

    def _metadata_matches_where(self, metadata: dict[str, Any], where: dict[str, Any] | None) -> bool:
        if not where:
            return True

        for key, expected in where.items():
            actual = metadata.get(key)
            if isinstance(expected, dict):
                if "$in" in expected:
                    candidates = {str(item) for item in expected.get("$in", [])}
                    if str(actual) not in candidates:
                        return False
                    continue
                return False
            if str(actual) != str(expected):
                return False
        return True

    def _tokenize(self, text: str) -> list[str]:
        tokens = TOKEN_PATTERN.findall(text.lower())
        return [token for token in tokens if len(token.strip()) >= 1]


def build_embedding_backend() -> tuple[str, EmbeddingFunction[Documents]]:
    model_name = DEFAULT_FASTEMBED_MODEL
    if model_name:
        try:
            embedding_function = FastEmbedEmbeddingFunction(
                model_name=model_name,
                device=DEFAULT_FASTEMBED_DEVICE,
                cache_dir=DEFAULT_FASTEMBED_CACHE_DIR,
            )
            version = f"fastembed-{model_name}"
            logger.info(
                "Using fastembed embedding model: %s on %s%s",
                model_name,
                DEFAULT_FASTEMBED_DEVICE,
                f" (cache_dir={DEFAULT_FASTEMBED_CACHE_DIR})" if DEFAULT_FASTEMBED_CACHE_DIR else "",
            )
            return version, embedding_function
        except Exception as exc:  # pragma: no cover - runtime fallback boundary
            logger.warning(
                "Failed to initialize fastembed embedding model %s, fallback to hash embedding: %s",
                model_name,
                exc,
            )

    return FALLBACK_EMBEDDING_VERSION, HashEmbeddingFunction()


def sanitize_collection_suffix(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip()).strip("_").lower()
    return sanitized or "default"
