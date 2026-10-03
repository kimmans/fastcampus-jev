"""Execute the tutorial notebooks in place and save their outputs.

Run: uv run python scripts/run_notebooks.py [name-fragment ...]
Calls the real Jev and chat model, so OPENROUTER_API_KEY must be set in .env.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

NOTEBOOK_DIR = Path(__file__).resolve().parent.parent / "notebooks"


def main() -> int:
    fragments = sys.argv[1:]
    failed = 0
    for path in sorted(NOTEBOOK_DIR.glob("*.ipynb")):
        if fragments and not any(fragment in path.name for fragment in fragments):
            continue
        notebook = nbformat.read(path, as_version=4)
        client = NotebookClient(
            notebook,
            timeout=600,
            kernel_name="python3",
            resources={"metadata": {"path": str(NOTEBOOK_DIR)}},
        )
        try:
            client.execute()
            status = "ok"
        except Exception as exc:  # noqa: BLE001 - report and keep partial outputs
            failed += 1
            status = f"FAILED: {str(exc)[-600:]}"
        nbformat.write(notebook, path)
        sys.stdout.write(f"{path.name}: {status}\n")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
