import os
import subprocess
import sys
from pathlib import Path

import pytest

from company_autopsy.analyze import analyze_dossier
from company_autopsy.fixtures import generate_fixtures
from company_autopsy.ingest import load_dossier, retrieve_quote
from company_autopsy.report import render_html, render_markdown


ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = source_path + (os.pathsep + existing if existing else "")
    return subprocess.run(
        [sys.executable, "-m", "company_autopsy", *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.fixture
def demo_root(tmp_path: Path) -> Path:
    root = tmp_path / "fixtures"
    generate_fixtures(root)
    return root


def test_fixture_generation_is_deterministic_and_plants_conflicts(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_fixtures(first)
    generate_fixtures(second)
    first_files = {
        path.relative_to(first).as_posix(): path.read_bytes()
        for path in first.rglob("*") if path.is_file()
    }
    second_files = {
        path.relative_to(second).as_posix(): path.read_bytes()
        for path in second.rglob("*") if path.is_file()
    }
    assert first_files == second_files
    pricing = (first / "northstar-ledger" / "pricing.md").read_text(encoding="utf-8")
    blog = (first / "northstar-ledger" / "blog.md").read_text(encoding="utf-8")
    assert "$39" in pricing
    assert "$49" in blog


def test_ingestion_assigns_ids_and_quotes_are_verbatim(demo_root: Path) -> None:
    materials, _, _ = load_dossier(demo_root / "northstar-ledger")
    assert materials
    assert len({material.source_id for material in materials}) == len(materials)
    analysis = analyze_dossier(str(demo_root / "northstar-ledger"))
    for claim in analysis.claims:
        for evidence in claim.evidence:
            assert retrieve_quote(analysis.materials, evidence.source_id, evidence.quote) == evidence.quote
            source = next(item for item in analysis.materials if item.source_id == evidence.source_id)
            assert evidence.quote in source.content


def test_classification_has_quotes_scores_and_inference_links(demo_root: Path) -> None:
    analysis = analyze_dossier(str(demo_root / "northstar-ledger"))
    observed = [claim for claim in analysis.claims if claim.tag == "OBSERVED"]
    inferred = [claim for claim in analysis.claims if claim.tag == "INFERRED"]
    assert observed and inferred
    assert all(claim.confidence == 0.99 and claim.evidence for claim in observed)
    assert all(0.0 <= claim.confidence <= 1.0 and claim.evidence for claim in inferred)
    assert all(claim.rule_id.startswith("inference:") for claim in inferred)
    assert all(item.quote for claim in analysis.claims for item in claim.evidence)


def test_planted_contradiction_keeps_and_cites_both_claims(demo_root: Path) -> None:
    analysis = analyze_dossier(str(demo_root / "northstar-ledger"))
    assert analysis.contradictions
    claims_by_id = {claim.claim_id: claim for claim in analysis.claims}
    contradiction = analysis.contradictions[0]
    left, right = (claims_by_id[claim_id] for claim_id in contradiction.claim_ids)
    amounts = {amount for amount in ("$39", "$49") if any(amount in claim.text for claim in (left, right))}
    assert amounts == {"$39", "$49"}
    assert left in analysis.claims and right in analysis.claims
    assert left.evidence[0].quote in next(
        material.content for material in analysis.materials if material.source_id == left.evidence[0].source_id
    )
    assert right.evidence[0].quote in next(
        material.content for material in analysis.materials if material.source_id == right.evidence[0].source_id
    )
    rendered = render_markdown(analysis)
    assert left.claim_id in rendered and right.claim_id in rendered
    assert '"Starting price: $39 per workspace monthly."' in rendered
    assert '"Starting price: $49 per workspace monthly."' in rendered


def test_same_dossier_produces_byte_identical_markdown(demo_root: Path) -> None:
    dossier = str(demo_root / "harborlight-repairs")
    first = render_markdown(analyze_dossier(dossier)).encode("utf-8")
    second = render_markdown(analyze_dossier(dossier)).encode("utf-8")
    assert first == second


def test_html_has_methodology_banner_and_observed_inferred_legend(demo_root: Path) -> None:
    analysis = analyze_dossier(str(demo_root / "northstar-ledger"))
    html = render_html(analysis)
    assert 'aria-label="Methodology banner"' in html
    assert "Methodology:" in html
    assert "OBSERVED" in html and "INFERRED" in html
    assert "fictional demo data" in html


def test_unmarked_input_is_labelled_as_unverified_public_data(tmp_path: Path) -> None:
    dossier = tmp_path / "unmarked"
    dossier.mkdir()
    (dossier / "notes.txt").write_text("Business model: The material says monthly service.\n", encoding="utf-8")
    report = render_markdown(analyze_dossier(str(dossier)))
    assert "public-data teardown, not verified with the company" in report
    assert "No inside knowledge" in report


def test_cli_fixtures_subcommand(tmp_path: Path) -> None:
    output = tmp_path / "generated"
    result = _run_cli("fixtures", "--out", str(output))
    assert result.returncode == 0, result.stderr
    assert "fictional material files" in result.stdout
    assert (output / "northstar-ledger" / "pricing.md").is_file()


def test_cli_teardown_subcommand_writes_both_reports(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    generate_fixtures(fixtures)
    output = tmp_path / "reports"
    result = _run_cli("teardown", "--in", str(fixtures / "northstar-ledger"), "--out", str(output))
    assert result.returncode == 0, result.stderr
    assert (output / "report.md").is_file()
    assert (output / "report.html").is_file()
    assert "Starting price statements disagree" in (output / "report.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("format_name, suffix", [("md", ".md"), ("html", ".html")])
def test_cli_report_subcommand(tmp_path: Path, format_name: str, suffix: str) -> None:
    fixtures = tmp_path / "fixtures"
    generate_fixtures(fixtures)
    output = tmp_path / ("report" + suffix)
    result = _run_cli(
        "report", "--in", str(fixtures / "meadow-metric"), "--format", format_name, "--out", str(output)
    )
    assert result.returncode == 0, result.stderr
    assert output.is_file()
    assert output.stat().st_size > 0
