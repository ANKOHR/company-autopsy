"""Read a dossier into a stable set of source materials."""

import json
from pathlib import Path

from .models import Material

SUPPORTED_SUFFIXES = {".md", ".txt"}
MANIFEST_NAME = ".company-autopsy.json"


def load_dossier(directory: str | Path) -> tuple[tuple[Material, ...], str, str]:
    """Return materials, company name, and honesty label for a dossier."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Dossier directory does not exist: {root}")

    paths = [
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    paths.sort(key=lambda path: path.relative_to(root).as_posix().casefold())
    materials = tuple(
        Material(
            source_id=f"SRC-{index:03d}",
            path=path.relative_to(root).as_posix(),
            content=path.read_text(encoding="utf-8"),
        )
        for index, path in enumerate(paths, start=1)
    )
    if not materials:
        raise ValueError("Dossier contains no .md or .txt material files")

    company_name = root.name
    label = "public-data teardown, not verified with the company"
    manifest_path = root / MANIFEST_NAME
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise ValueError(f"Invalid dossier manifest: {manifest_path}") from error
        if not isinstance(manifest, dict):
            raise ValueError("Dossier manifest must contain a JSON object")
        if isinstance(manifest.get("company_name"), str) and manifest["company_name"].strip():
            company_name = manifest["company_name"].strip()
        if manifest.get("fictional") is True and manifest.get("fixture") is True:
            label = "fictional demo data"

    return materials, company_name, label


def retrieve_quote(materials: tuple[Material, ...], source_id: str, quote: str) -> str:
    """Verify and return an exact quote from its named source."""
    for material in materials:
        if material.source_id == source_id:
            if quote not in material.content:
                raise ValueError(f"Quote is not present verbatim in {source_id}")
            return quote
    raise KeyError(f"Unknown source id: {source_id}")
