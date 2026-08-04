"""Lesson 1: render the hand-authored pyXDSM diagram of the ASW model.

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_01_dsm/generate_xdsm.py

This reuses the example's XDSM builder
(``aircraft_sizing.examples.ex_01_asw.viz.xdsm.asw_sizing_xdsm``), which renders a
publication-quality PDF/PNG via LaTeX, and copies the results into ``outputs/``.
Rendering needs ``pdflatex`` (TeX Live/MiKTeX) and, for the PNG, ``pdftoppm``
(poppler) on PATH.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aircraft_sizing.examples.ex_01_asw.viz.xdsm import asw_sizing_xdsm as xdsm_module  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        rendered = xdsm_module.render()
    except xdsm_module.MissingPrerequisiteError as exc:
        print(exc, file=sys.stderr)
        return 1

    for path in rendered:
        if path.suffix in (".png", ".pdf"):
            destination = OUTPUT_DIR / f"asw_xdsm{path.suffix}"
            shutil.copy2(path, destination)
            print(f"Wrote {destination.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
