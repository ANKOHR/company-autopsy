"""Small immutable records shared by ingestion, analysis, and reporting."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    source_id: str
    path: str
    content: str


@dataclass(frozen=True)
class Evidence:
    source_id: str
    quote: str


@dataclass(frozen=True)
class Claim:
    claim_id: str
    dimension: str
    text: str
    tag: str
    confidence: float
    evidence: tuple[Evidence, ...]
    rule_id: str


@dataclass(frozen=True)
class Contradiction:
    contradiction_id: str
    key: str
    summary: str
    claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class Analysis:
    company_name: str
    label: str
    materials: tuple[Material, ...]
    claims: tuple[Claim, ...]
    contradictions: tuple[Contradiction, ...]
