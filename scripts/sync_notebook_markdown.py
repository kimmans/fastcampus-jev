"""Copy markdown cells from the notebook sources into the saved notebooks, keeping code outputs.

Run: uv run python scripts/sync_notebook_markdown.py [name-fragment ...]
Use this after editing prose only. Rebuilding with build_notebooks.py clears the saved outputs.
"""

from __future__ import annotations

import sys

import nbformat
from build_notebooks import NOTEBOOKS, OUT


def main() -> int:
    fragments = sys.argv[1:]
    for name, cells in NOTEBOOKS.items():
        if fragments and not any(fragment in name for fragment in fragments):
            continue
        path = OUT / name
        notebook = nbformat.read(path, as_version=4)
        if len(notebook.cells) != len(cells):
            sys.stdout.write(f"{name}: skipped (cell count differs, rebuild instead)\n")
            continue
        for cell, (kind, source) in zip(notebook.cells, cells, strict=True):
            if kind == "md" and cell.cell_type == "markdown":
                cell.source = source
        nbformat.write(notebook, path)
        sys.stdout.write(f"{name}: markdown synced\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
