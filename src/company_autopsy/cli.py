"""Command line interface for generating fixtures and reports."""

import argparse
import sys
from pathlib import Path

from .analyze import analyze_dossier
from .fixtures import generate_fixtures
from .report import render_html, render_markdown


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-autopsy",
        description="Build evidence-linked teardowns from supplied public-style material.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    fixtures = commands.add_parser("fixtures", help="generate fictional demo dossiers")
    fixtures.add_argument("--out", required=True, help="directory to receive the dossiers")

    teardown = commands.add_parser("teardown", help="analyze a dossier and write Markdown plus HTML")
    teardown.add_argument("--in", dest="input_directory", required=True, help="dossier directory")
    teardown.add_argument("--out", required=True, help="directory for report.md and report.html")

    report = commands.add_parser("report", help="render one report format from a dossier")
    report.add_argument("--in", dest="input_directory", required=True, help="dossier directory")
    report.add_argument("--format", choices=("md", "html"), required=True)
    report.add_argument("--out", help="output file, or stdout when omitted")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "fixtures":
            written = generate_fixtures(args.out)
            print(f"Generated {len(written)} fictional material files in {Path(args.out).resolve()}")
            return 0

        analysis = analyze_dossier(args.input_directory)
        if args.command == "teardown":
            output = Path(args.out).expanduser().resolve()
            output.mkdir(parents=True, exist_ok=True)
            markdown_path = output / "report.md"
            html_path = output / "report.html"
            markdown_path.write_text(render_markdown(analysis), encoding="utf-8", newline="\n")
            html_path.write_text(render_html(analysis), encoding="utf-8", newline="\n")
            print(f"Wrote {markdown_path}")
            print(f"Wrote {html_path}")
            return 0

        rendered = render_markdown(analysis) if args.format == "md" else render_html(analysis)
        if args.out:
            output = Path(args.out).expanduser().resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8", newline="\n")
            print(f"Wrote {output}")
        else:
            sys.stdout.write(rendered)
        return 0
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"company-autopsy: error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
