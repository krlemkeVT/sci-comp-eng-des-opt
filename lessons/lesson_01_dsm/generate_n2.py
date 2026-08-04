"""Lesson 1: generate the OpenMDAO N2 diagram for the ASW sizing model.

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_01_dsm/generate_n2.py

OpenMDAO reads the model it was handed and writes an interactive HTML N2 diagram.
Open ``outputs/asw_n2.html`` in a browser and click the ``struct`` / ``sizing``
cells to see the one feedback connection highlighted.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import openmdao.api as om  # noqa: E402

from aircraft_sizing.examples.ex_01_asw.methods.config import ASWSizingInputs  # noqa: E402
from aircraft_sizing.examples.ex_01_asw.methods.group import build_asw_problem  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    inputs = ASWSizingInputs.baseline()
    problem = build_asw_problem(inputs.params(), inputs.input_values(), solver="nlbgs")
    problem.run_model()

    outfile = OUTPUT_DIR / "asw_n2.html"
    om.n2(problem, outfile=str(outfile), show_browser=False)
    print(f"Wrote {outfile.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
