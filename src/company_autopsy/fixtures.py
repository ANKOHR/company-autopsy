"""Curated, fictional demo dossiers with deterministic planted conflicts."""

import json
from pathlib import Path

FIXTURE_SEED = 20260928

DOSSIERS: dict[str, dict[str, str]] = {
    "northstar-ledger": {
        "homepage.md": """# Northstar Ledger

Business model: We sell a subscription bookkeeping service for independent design studios.
Customer journey: A studio books a discovery call, connects its bank account, and reviews a monthly close in the dashboard.
Operational bottleneck: Our operations team copies emailed receipts into the ledger by hand.
""",
        "pricing.md": """# Pricing

Starting price: $39 per workspace monthly.
""",
        "careers.md": """# Operations associate

Likely software stack: The team uses LedgerFox, Google Sheets, and a shared support inbox.
Operational risk: Month-end close can be delayed when clients submit receipts late.
""",
        "blog.md": """# A note on plans

Starting price: $49 per workspace monthly.
AI or automation opportunity: We are exploring automatic receipt matching before a bookkeeper reviews each close.
""",
    },
    "harborlight-repairs": {
        "homepage.md": """# Harborlight Repairs

Business model: We coordinate appliance repairs and charge customers for each completed visit.
Customer journey: A customer submits a repair form, receives a time window, and gets a completion note by email.
Operational bottleneck: Dispatchers re-enter customer details from the form into a daily spreadsheet.
""",
        "pricing.md": """# Service rates

Starting price: $85 per visit.
""",
        "careers.md": """# Dispatcher

Likely software stack: Dispatch uses FixFlow, Google Sheets, and email.
Operational risk: A technician can miss an address update when a job is reassigned.
""",
        "blog.md": """# Better repair updates

AI or automation opportunity: We want to send appointment reminders when a technician is on the way.
""",
    },
    "meadow-metric": {
        "homepage.md": """# Meadow Metric

Business model: We provide annual subscription analytics for small farms.
Customer journey: A farm requests a trial, imports field records, and reviews crop summaries with an advisor.
Operational bottleneck: Advisors manually reconcile inconsistent field names before a review.
""",
        "pricing.md": """# Plans

Starting price: $240 per farm annually.
""",
        "careers.md": """# Data advisor

Likely software stack: Advisors use FieldNote, spreadsheets, and video calls.
Operational risk: Missing field records can make a seasonal comparison incomplete.
""",
        "blog.md": """# Product update

AI or automation opportunity: We are prototyping a field-name matcher for advisor review.
""",
    },
}


def generate_fixtures(output_directory: str | Path) -> tuple[Path, ...]:
    """Write all fixed fictional dossiers without using random values."""
    root = Path(output_directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for slug in sorted(DOSSIERS):
        dossier_path = root / slug
        dossier_path.mkdir(parents=True, exist_ok=True)
        manifest = {
            "company_name": slug.replace("-", " ").title(),
            "fixture": True,
            "fictional": True,
            "seed": FIXTURE_SEED,
        }
        (dossier_path / ".company-autopsy.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        for filename in sorted(DOSSIERS[slug]):
            path = dossier_path / filename
            path.write_text(DOSSIERS[slug][filename], encoding="utf-8", newline="\n")
            written.append(path)
    return tuple(written)
