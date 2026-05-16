"""Generate wiki-derived FAQ entries for the research-bot widget.

Reads the LLM wiki at WIKI_ROOT (default: /Users/nguyenmn/research-wiki/),
rewrites entries with `source: wiki` in data/research_bot.yaml, and
refreshes tests/fixtures/research_bot.json so the node matcher tests
still pass. Hand-authored entries are preserved verbatim.

This file is intentionally one module; functions are small and pure so
that they can be exercised individually from
tests/test_build_faq_from_wiki.py.

Usage:
    python3 scripts/build_faq_from_wiki.py [WIKI_ROOT]

Exit codes:
    0 success (file rewritten or unchanged)
    2 usage error
    3 wiki root invalid or no SRC records found
    4 a SRC record is malformed
    5 a bucket map entry references an unknown SRC ID
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    raise NotImplementedError("filled in by subsequent tasks")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
