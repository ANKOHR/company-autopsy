"""Deterministic Markdown and HTML report renderers."""

from html import escape

from .models import Analysis, Claim, Evidence

METHODOLOGY = (
    "OBSERVED claims repeat statements found in supplied material and cite an exact quote. "
    "INFERRED claims are rule-based interpretations and link to the source statements that support them. "
    "Neither label means the company has independently verified the statement."
)


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _evidence_text(evidence: tuple[Evidence, ...]) -> str:
    return "; ".join(f'{item.source_id}: "{item.quote}"' for item in evidence)


def _claim_table(claims: tuple[Claim, ...]) -> list[str]:
    lines = [
        "| ID | Area | Claim | Tag | Confidence | Evidence |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for claim in claims:
        lines.append(
            "| " + " | ".join(
                _md(value) for value in (
                    claim.claim_id,
                    claim.dimension,
                    claim.text,
                    claim.tag,
                    f"{claim.confidence:.2f}",
                    _evidence_text(claim.evidence),
                )
            ) + " |"
        )
    return lines


def render_markdown(analysis: Analysis) -> str:
    label = analysis.label
    if label == "fictional demo data":
        honesty = "All company names and materials in this dossier are fictional demo data."
    else:
        honesty = (
            "This is a public-data teardown, not verified with the company. "
            "No inside knowledge or confirmed business details are claimed."
        )
    lines = [
        f"# Company Autopsy: {_md(analysis.company_name)}",
        "",
        "> **Methodology:** " + METHODOLOGY,
        f"> **Dataset label:** {honesty}",
        "> **Legend:** OBSERVED means stated in supplied material. INFERRED means derived by the documented rules. Confidence is a heuristic support score, not a calibrated probability.",
        "",
        "## Claim ledger",
        "",
    ]
    if analysis.claims:
        lines.extend(_claim_table(analysis.claims))
    else:
        lines.append("No supported claims were extracted from the recognized field labels.")

    focused_sections = (
        ("Bottlenecks", {"Bottleneck"}),
        ("AI and automation opportunities", {"Opportunities"}),
    )
    for title, dimensions in focused_sections:
        lines.extend(["", f"## {title}", ""])
        selected = [claim for claim in analysis.claims if claim.dimension in dimensions]
        if selected:
            lines.append("Claim IDs: " + ", ".join(claim.claim_id for claim in selected) + ".")
            for claim in selected:
                lines.append(f"- **{claim.tag}, {claim.confidence:.2f}:** {_md(claim.text)}")
        else:
            lines.append("No claims in this area were supported by the supplied material.")

    lines.extend(["", "## Contradictions", ""])
    claims_by_id = {claim.claim_id: claim for claim in analysis.claims}
    if analysis.contradictions:
        for contradiction in analysis.contradictions:
            lines.append(f"### {contradiction.contradiction_id}: {contradiction.summary}")
            for claim_id in contradiction.claim_ids:
                claim = claims_by_id[claim_id]
                lines.append(
                    f"- **{claim.claim_id}, {claim.tag}, {claim.confidence:.2f}:** "
                    f"{_md(claim.text)} Evidence: {_md(_evidence_text(claim.evidence))}"
                )
            lines.append("")
    else:
        lines.append("No contradictions were detected by the current explicit starting-price comparison rule.")

    lines.extend(["## Source materials", ""])
    for material in analysis.materials:
        lines.append(f"- **{material.source_id}:** `{_md(material.path)}`")
    lines.append("")
    return "\n".join(lines)


def _html_evidence(evidence: tuple[Evidence, ...]) -> str:
    return "; ".join(
        f'<span class="evidence"><strong>{escape(item.source_id)}</strong>: '
        f'&ldquo;{escape(item.quote)}&rdquo;</span>'
        for item in evidence
    )


def render_html(analysis: Analysis) -> str:
    if analysis.label == "fictional demo data":
        honesty = "All company names and materials in this dossier are fictional demo data."
    else:
        honesty = (
            "Public-data teardown, not verified with the company. "
            "No inside knowledge or confirmed business details are claimed."
        )
    rows = []
    for claim in analysis.claims:
        rows.append(
            "<tr>"
            f"<td>{escape(claim.claim_id)}</td>"
            f"<td>{escape(claim.dimension)}</td>"
            f"<td>{escape(claim.text)}</td>"
            f'<td><span class="tag {claim.tag.lower()}">{escape(claim.tag)}</span></td>'
            f"<td>{claim.confidence:.2f}</td>"
            f"<td>{_html_evidence(claim.evidence)}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="6">No supported claims were extracted.</td></tr>')

    claims_by_id = {claim.claim_id: claim for claim in analysis.claims}
    contradiction_items = []
    for contradiction in analysis.contradictions:
        cited_claims = []
        for claim_id in contradiction.claim_ids:
            claim = claims_by_id[claim_id]
            cited_claims.append(
                f'<li><strong>{escape(claim.claim_id)} {escape(claim.tag)} '
                f'({claim.confidence:.2f})</strong>: {escape(claim.text)}. '
                f"{_html_evidence(claim.evidence)}</li>"
            )
        contradiction_items.append(
            f'<article class="contradiction"><h3>{escape(contradiction.contradiction_id)}: '
            f"{escape(contradiction.summary)}</h3><ul>{''.join(cited_claims)}</ul></article>"
        )
    if not contradiction_items:
        contradiction_items.append(
            "<p>No contradictions were detected by the current explicit starting-price comparison rule.</p>"
        )

    focus_sections = []
    for title, dimension in (
        ("Bottlenecks", "Bottleneck"),
        ("AI and automation opportunities", "Opportunities"),
    ):
        selected = [claim for claim in analysis.claims if claim.dimension == dimension]
        if selected:
            items = "".join(
                f'<li><strong>{escape(claim.claim_id)} {escape(claim.tag)} '
                f'({claim.confidence:.2f})</strong>: {escape(claim.text)}</li>'
                for claim in selected
            )
            body = f"<ul>{items}</ul>"
        else:
            body = "<p>No claims in this area were supported by the supplied material.</p>"
        focus_sections.append(f"<section><h2>{escape(title)}</h2>{body}</section>")

    sources = "".join(
        f'<li><strong>{escape(material.source_id)}</strong>: '
        f"<code>{escape(material.path)}</code></li>"
        for material in analysis.materials
    )
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>Company Autopsy: {escape(analysis.company_name)}</title>",
            "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:1200px;margin:2rem auto;padding:0 1rem;color:#17202a}"
            ".banner{background:#edf5ff;border-left:5px solid #2767a8;padding:1rem;margin:1rem 0}"
            "table{border-collapse:collapse;width:100%;font-size:.92rem}th,td{border:1px solid #c8d0d8;padding:.55rem;text-align:left;vertical-align:top}"
            "th{background:#f3f5f7}.tag{font-weight:700}.observed{color:#17613a}.inferred{color:#8a4b00}"
            ".evidence{display:block;margin:.2rem 0}.contradiction{border-left:4px solid #bd3c35;padding:.2rem 1rem;margin:1rem 0}"
            "</style></head><body>",
            f"<h1>Company Autopsy: {escape(analysis.company_name)}</h1>",
            '<aside class="banner" aria-label="Methodology banner">',
            f"<p><strong>Methodology:</strong> {escape(METHODOLOGY)}</p>",
            f"<p><strong>Dataset label:</strong> {escape(honesty)}</p>",
            '<p><strong>Legend:</strong> <span class="tag observed">OBSERVED</span> means stated in supplied material. '
            '<span class="tag inferred">INFERRED</span> means derived by the documented rules. '
            "Confidence is a heuristic support score, not a calibrated probability.</p>",
            "</aside>",
            "<section><h2>Claim ledger</h2><table><thead><tr>",
            "<th>ID</th><th>Area</th><th>Claim</th><th>Tag</th><th>Confidence</th><th>Evidence</th>",
            "</tr></thead><tbody>",
            *rows,
            "</tbody></table></section>",
            *focus_sections,
            '<section><h2>Contradictions</h2>',
            *contradiction_items,
            "</section>",
            f"<section><h2>Source materials</h2><ul>{sources}</ul></section>",
            "</body></html>",
            "",
        ]
    )
