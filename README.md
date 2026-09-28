# Company Autopsy

Company Autopsy turns a directory of supplied company materials into an evidence-linked operational teardown. It extracts supported statements, labels them OBSERVED or INFERRED, assigns a rule-based confidence score, retains contradictory evidence, and writes Markdown and HTML reports.

> Company Autopsy tells you what it found in the supplied material, what it inferred, and how strongly the rules support each inference. It does not claim access to a company's internal systems or people.

## Quickstart

Python 3.10 or newer is required. The application uses the Python standard library and runs on CPU. Pytest is needed only to run the development test suite.

```powershell
python -m pip install -e .
company-autopsy fixtures --out demo
company-autopsy teardown --in demo/northstar-ledger --out reports/northstar-ledger
company-autopsy report --in demo/northstar-ledger --format html --out reports/northstar-ledger/preview.html
```

The fixtures command writes three synthetic dossiers. The teardown command writes `report.md` and `report.html`. The report command renders one requested format, or writes it to standard output when `--out` is omitted.

To run the tests:

```powershell
python -m pytest
```

## Architecture

```text
Markdown or text dossier files
            |
            v
Sorted ingestion assigns stable SRC identifiers and preserves source text
            |
            v
Field rules extract OBSERVED claims with exact source quotes
            |
            +----> Inference rules link support and calculate confidence
            |
            +----> Starting-price comparison flags conflicting claim pairs
            |
            v
Markdown and HTML renderers show claims, evidence, and contradictions
```

The parser reads `.md` and `.txt` files recursively in case-insensitive relative-path order. Each file receives a stable source ID such as `SRC-001`. Source IDs are scoped to one dossier. Quotes can be retrieved and checked verbatim with the ingestion API.

## Honesty boundary

All built-in demos are synthetic and explicitly marked as fictional demo data. They are generated locally from fixed templates, and do not describe real companies. If input has no generated-fixture manifest, reports say **public-data teardown, not verified with the company**. An OBSERVED label means a statement appeared in the supplied material. It does not mean the statement was independently checked or confirmed by the company. An INFERRED label means a documented rule derived an interpretation from cited material. No output claims inside knowledge.

The dossier manifest is `.company-autopsy.json`. The fixture generator writes the `fictional` and `fixture` flags and a company name. The report uses the fictional label only when both flags are true.

## Claim ontology

The extractor recognizes these explicit field labels, case-insensitively:

| Input label | Claim area |
| --- | --- |
| `Business model:` | Business model |
| `Customer journey:` | Customer journey |
| `Likely software stack:` | Software stack |
| `Operational bottleneck:` | Bottleneck |
| `Operational risk:` | Risk |
| `AI or automation opportunity:` | Opportunity |
| `Starting price:` | Pricing |

Each extracted claim has an ID, area, text, tag, confidence, rule ID, and one or more evidence links. An evidence link contains a source ID and an exact quote from that source. An observed claim quotes the matched field line. Inferred claims link to the observed lines that triggered their rule.

## Confidence rubric

Confidence is a deterministic support score, not a calibrated probability or guarantee of truth.

| Claim type | Score rule |
| --- | --- |
| OBSERVED | `0.99` when a supported field line is present and quoted verbatim |
| INFERRED | `min(0.90, 0.60 + 0.08 * (distinct supporting source count - 1))` |

The recurring-revenue inference requires a supported business-model or starting-price statement containing terms such as subscription, monthly, or annual. The workflow-automation inference requires an operational-bottleneck statement containing a manual-work signal such as spreadsheet, by hand, re-enter, or reconcile. Additional independent source files increase an inference score according to the formula. Repeated evidence in one file does not increase it.

## Contradictions and limits

The current contradiction rule compares explicit `Starting price:` claims when both sides include a currency and amount. Every disagreeing pair is shown with the two claims and their source quotes. The report keeps both claims in the ledger. It does not select a winner. Other contradictions are not yet detected automatically, so review the source material before relying on a teardown.

The extractor intentionally requires the field labels above. It does not perform web crawling, semantic search, private-data access, or machine-learning inference. Materials that do not use recognized labels remain available as sources but do not produce claims. This keeps the current extraction rules auditable and deterministic.

## Determinism and runtime

Fixture generation writes fixed curated templates and does not call a random-number generator. The documented fixture seed is `20260928`, stored in each manifest for provenance. Sorted file order, stable source and claim IDs, fixed confidence formulas, and deterministic rendering make repeated reports byte-identical for unchanged input. The program has no model, CUDA, torch, TensorFlow, or other GPU dependency.
