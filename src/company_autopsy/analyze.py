"""Rule-based claim extraction, inference, and contradiction detection."""

import re
from dataclasses import dataclass

from .ingest import load_dossier
from .models import Analysis, Claim, Contradiction, Evidence, Material

FIELD_RULES = {
    "business model": ("business_model", "Business model", "Business model"),
    "customer journey": ("customer_journey", "Customer journey", "Customer journey"),
    "likely software stack": ("software_stack", "Likely software stack", "Software stack"),
    "operational bottleneck": ("bottleneck", "Operational bottleneck", "Bottleneck"),
    "operational risk": ("risk", "Operational risk", "Risk"),
    "ai or automation opportunity": ("opportunity", "AI or automation opportunity", "Opportunity"),
    "starting price": ("starting_price", "Starting price", "Pricing"),
}
FIELD_PATTERN = re.compile(
    r"^\s*(Business model|Customer journey|Likely software stack|"
    r"Operational bottleneck|Operational risk|AI or automation opportunity|"
    r"Starting price)\s*:\s*(.+?)\s*$",
    re.IGNORECASE,
)
RECURRING_PATTERN = re.compile(
    r"\b(subscription|subscriptions|monthly|annually|annual|recurring|per month|per year)\b",
    re.IGNORECASE,
)
AUTOMATION_PATTERN = re.compile(
    r"\b(manual(?:ly)?|by hand|spreadsheet|re-enter|reenter|copy|copies|handoff|queue|reconcile)\b",
    re.IGNORECASE,
)
PRICE_PATTERN = re.compile(
    r"(?P<currency>USD|EUR|GBP|\$|€|£)\s*"
    r"(?P<amount>\d+(?:,\d{3})*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _Fact:
    key: str
    value: str
    claim: Claim


def _confidence_for_inference(evidence: tuple[Evidence, ...]) -> float:
    source_count = len({item.source_id for item in evidence})
    return min(0.90, round(0.60 + 0.08 * max(0, source_count - 1), 2))


def _evidence_for(facts: list[_Fact]) -> tuple[Evidence, ...]:
    seen: set[tuple[str, str]] = set()
    evidence: list[Evidence] = []
    for fact in facts:
        for item in fact.claim.evidence:
            key = (item.source_id, item.quote)
            if key not in seen:
                seen.add(key)
                evidence.append(item)
    return tuple(evidence)


def _money(value: str) -> tuple[str, float] | None:
    match = PRICE_PATTERN.search(value)
    if not match:
        return None
    currency = match.group("currency").upper()
    currency = {"$": "USD", "€": "EUR", "£": "GBP"}.get(currency, currency)
    return currency, float(match.group("amount").replace(",", ""))


def _contradictions(facts: list[_Fact]) -> tuple[Contradiction, ...]:
    """Flag every disagreeing pair of explicit starting-price statements."""
    prices = [fact for fact in facts if fact.key == "starting_price" and _money(fact.value)]
    results: list[Contradiction] = []
    for left_index, left in enumerate(prices):
        left_money = _money(left.value)
        for right in prices[left_index + 1 :]:
            right_money = _money(right.value)
            if left_money != right_money:
                results.append(
                    Contradiction(
                        contradiction_id=f"X{len(results) + 1:03d}",
                        key="starting_price",
                        summary="Starting price statements disagree. Both claims are retained.",
                        claim_ids=(left.claim.claim_id, right.claim.claim_id),
                    )
                )
    return tuple(results)


def analyze_materials(
    materials: tuple[Material, ...], company_name: str, label: str
) -> Analysis:
    facts: list[_Fact] = []
    claims: list[Claim] = []
    for material in materials:
        for raw_line in material.content.splitlines():
            match = FIELD_PATTERN.match(raw_line)
            if not match:
                continue
            original_label = match.group(1).lower()
            field_key, _source_label, display_label = FIELD_RULES[original_label]
            value = match.group(2).strip()
            quote = match.group(0).strip()
            if not value or quote not in material.content:
                continue
            claim = Claim(
                claim_id=f"C{len(claims) + 1:03d}",
                dimension=display_label,
                text=f"{display_label}: {value}",
                tag="OBSERVED",
                confidence=0.99,
                evidence=(Evidence(material.source_id, quote),),
                rule_id=f"observed:{field_key}",
            )
            claims.append(claim)
            facts.append(_Fact(field_key, value, claim))

    inference_specs: list[tuple[str, str, str, list[_Fact]]] = []
    recurring_support = [
        fact for fact in facts
        if fact.key in {"business_model", "starting_price"}
        and RECURRING_PATTERN.search(fact.value)
    ]
    if recurring_support:
        inference_specs.append(
            (
                "Business model",
                "Recurring payments likely form part of the revenue model.",
                "inference:recurring_revenue",
                recurring_support,
            )
        )

    automation_support = [
        fact for fact in facts
        if fact.key == "bottleneck" and AUTOMATION_PATTERN.search(fact.value)
    ]
    if automation_support:
        inference_specs.append(
            (
                "Opportunities",
                "The described operational bottleneck may be suitable for workflow automation.",
                "inference:workflow_automation_candidate",
                automation_support,
            )
        )

    for dimension, text, rule_id, supporting_facts in inference_specs:
        evidence = _evidence_for(supporting_facts)
        claims.append(
            Claim(
                claim_id=f"C{len(claims) + 1:03d}",
                dimension=dimension,
                text=text,
                tag="INFERRED",
                confidence=_confidence_for_inference(evidence),
                evidence=evidence,
                rule_id=rule_id,
            )
        )

    return Analysis(
        company_name=company_name,
        label=label,
        materials=materials,
        claims=tuple(claims),
        contradictions=_contradictions(facts),
    )


def analyze_dossier(directory: str) -> Analysis:
    materials, company_name, label = load_dossier(directory)
    return analyze_materials(materials, company_name, label)
