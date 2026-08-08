"""Lesson 1: render small XDSM examples for the other pyXDSM node "shapes".

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_01_dsm/generate_shapes.py

The ASW diagram (``generate_xdsm.py``) only uses two shapes: the analysis box
(``FUNC``) and the solver (``SOLVER``). This script renders one tiny diagram for
each of the *other* shapes you meet in real MDO diagrams:

- ``OPT`` — an optimizer (blue pill),
- ``DOE`` — a design-of-experiments driver (blue pill),
- ``stack=True`` — the decoration for parallel/repeated instances,
- ``SUBOPT`` — a bi-level optimization (blue chamfered box, nested under ``OPT``),
- ``SOLVER`` (``MDA``) — a solver, in its minimal canonical form (orange pill),
- ``METAMODEL`` — a surrogate standing in for an analysis (yellow rectangle),
- ``GROUP`` — a bundle of components exposed as one sub-block (green chamfered),
- ``IFUNC``/``IGROUP`` — the *implicit* variants that expose residuals to an
  outer solver (salmon rectangle / chamfered box).

Each figure is written to ``outputs/`` as PNG and PDF so the lesson renders on
GitHub without re-running anything.

The shapes and their meaning follow the XDSM conventions of Lambe & Martins
(2012), "Extensions to the Design Structure Matrix for the Description of
Multidisciplinary Design, Analysis, and Optimization Processes", and the
examples shipped with pyXDSM (https://github.com/mdolab/pyXDSM).

Rendering needs ``pdflatex`` (TeX Live/MiKTeX) and, for the PNG, ``pdftoppm``
(poppler) on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
REPO_ROOT = Path(__file__).resolve().parents[2]


class MissingPrerequisiteError(RuntimeError):
    """Raised when a rendering prerequisite is unavailable."""


def _pyxdsm_api():
    try:
        from pyxdsm.XDSM import (
            DOE,
            FUNC,
            GROUP,
            IFUNC,
            IGROUP,
            METAMODEL,
            OPT,
            RIGHT,
            SOLVER,
            SUBOPT,
            XDSM,
        )
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise MissingPrerequisiteError(
            "Missing prerequisite: Python package 'pyXDSM' is not installed in the active "
            "environment. Install it, then rerun this script from the repository root."
        ) from exc

    return {
        "XDSM": XDSM,
        "OPT": OPT,
        "SUBOPT": SUBOPT,
        "SOLVER": SOLVER,
        "DOE": DOE,
        "FUNC": FUNC,
        "METAMODEL": METAMODEL,
        "GROUP": GROUP,
        "IFUNC": IFUNC,
        "IGROUP": IGROUP,
        "RIGHT": RIGHT,
    }


# --------------------------------------------------------------------------- #
# One builder per shape. Each returns a small, self-contained XDSM.
# --------------------------------------------------------------------------- #
def build_optimization(api):
    """OPT — a single optimizer driving one analysis.

    The green rounded box owns the design variables and iterates the analysis
    until an optimality (KKT) target is met. The edge below the diagonal
    (``f, g`` back to the optimizer) is the optimization loop.
    """
    XDSM, OPT, FUNC, RIGHT = api["XDSM"], api["OPT"], api["FUNC"], api["RIGHT"]
    x = XDSM(use_sfmath=False)

    x.add_system("opt", OPT, (r"\text{Optimizer}",))
    x.add_system("analysis", FUNC, (r"\text{Analysis}",))

    x.add_input("opt", r"x^{(0)}")
    x.connect("opt", "analysis", r"x")
    x.connect("analysis", "opt", r"f,\ g")
    x.add_output("opt", r"x^{*}", side=RIGHT)

    x.add_process(["opt", "analysis", "opt"], arrow=True)
    return x


def build_doe(api):
    """DOE — a design-of-experiments driver sampling one analysis.

    Unlike an optimizer, a DOE driver has no optimality target: it evaluates the
    model at a *designed* set of points (full factorial, Latin hypercube, ...)
    to explore, screen, or fit a surrogate. The analysis is ``stack``ed because
    the same box is evaluated once per sample.
    """
    XDSM, DOE, FUNC, RIGHT = api["XDSM"], api["DOE"], api["FUNC"], api["RIGHT"]
    x = XDSM(use_sfmath=False)

    x.add_system("doe", DOE, (r"\text{DOE driver}",))
    x.add_system("analysis", FUNC, (r"\text{Analysis}",), stack=True)

    x.add_input("doe", (r"x_L,\ x_U,\ N"))
    x.connect("doe", "analysis", r"x^{(i)}", stack=True)
    x.connect("analysis", "doe", r"f^{(i)},\ g^{(i)}", stack=True)
    x.add_output("doe", r"\{x^{(i)},\ f^{(i)},\ g^{(i)}\}", side=RIGHT)

    x.add_process(["doe", "analysis", "doe"], arrow=True)
    return x


def build_bilevel(api):
    """SUBOPT under OPT — a bi-level (nested) optimization.

    A system-level optimizer sets the shared/target variables ``z``; each
    discipline runs its *own* sub-optimizer that minimizes a local objective and
    returns the optimized value ``J_i^*`` upward. Two nested optimization loops.
    The discipline sub-optimizer and its analysis are ``stack``ed because there
    is one per discipline, solved independently (Collaborative-Optimization
    style).
    """
    XDSM, OPT, SUBOPT, FUNC, RIGHT = (
        api["XDSM"],
        api["OPT"],
        api["SUBOPT"],
        api["FUNC"],
        api["RIGHT"],
    )
    x = XDSM(use_sfmath=False)

    x.add_system("sysopt", OPT, (r"\text{System}", r"\text{optimizer}"))
    x.add_system("subopt", SUBOPT, (r"\text{Discipline}", r"\text{optimizer}"), stack=True)
    x.add_system("analysis", FUNC, (r"\text{Discipline}", r"\text{analysis}"), stack=True)

    x.add_input("sysopt", r"z^{(0)}")
    x.connect("sysopt", "subopt", r"z", stack=True)
    x.connect("subopt", "analysis", r"x_i,\ z", stack=True)
    x.connect("analysis", "subopt", r"y_i", stack=True)
    x.connect("subopt", "sysopt", r"J_i^{*}", stack=True)
    x.add_output("sysopt", r"z^{*}", side=RIGHT)

    x.add_process(["sysopt", "subopt", "analysis", "subopt", "sysopt"], arrow=True)
    return x


def build_stack(api):
    """stack=True — many independent instances of the same component.

    The stacked box means the analysis is evaluated once per case ``j`` (flight
    condition, load case, DOE sample, scenario). The instances are uncoupled and
    can run in parallel; the ``aggregate`` box rolls the per-case results into a
    single objective/constraint. Here an optimizer sizes a design while the
    aerodynamics box is evaluated across several flight conditions at once.
    """
    XDSM, OPT, FUNC, RIGHT = api["XDSM"], api["OPT"], api["FUNC"], api["RIGHT"]
    x = XDSM(use_sfmath=False)

    x.add_system("opt", OPT, (r"\text{Optimizer}",))
    x.add_system("aero", FUNC, (r"\text{Aerodynamics}",), stack=True)
    x.add_system("agg", FUNC, (r"\text{Aggregate}",))

    x.add_input("opt", r"x^{(0)}")
    x.connect("opt", "aero", r"x,\ M_j,\ \alpha_j", stack=True)
    x.connect("aero", "agg", r"(L/D)_j,\ C_{L,j}", stack=True)
    x.connect("agg", "opt", r"f,\ g")
    x.add_output("opt", r"x^{*}", side=RIGHT)

    x.add_process(["opt", "aero", "agg", "opt"], arrow=True)
    return x


def build_solver(api):
    """SOLVER (MDA) — the shape you already met in the ASW diagram, minimal form.

    A solver is a driver like the optimizer, but its target is *feasibility*, not
    optimality: it drives the coupled disciplines to self-consistency. Here is the
    canonical two-discipline Gauss-Seidel MDA — Discipline 1 needs `y_2` from
    Discipline 2 and vice versa, so the solver iterates the guess `y_2` until the
    returned value matches (the edge below the diagonal is the coupling loop).
    """
    XDSM, SOLVER, FUNC, RIGHT = api["XDSM"], api["SOLVER"], api["FUNC"], api["RIGHT"]
    x = XDSM(use_sfmath=False)

    x.add_system("solver", SOLVER, (r"\text{MDA}", r"\text{solver}"))
    x.add_system("disc1", FUNC, (r"\text{Discipline 1}",))
    x.add_system("disc2", FUNC, (r"\text{Discipline 2}",))

    x.add_input("solver", r"y_2^{(0)}")
    x.connect("solver", "disc1", r"y_2")
    x.connect("disc1", "disc2", r"y_1")
    x.connect("disc2", "solver", r"y_2")
    x.add_output("solver", r"y_1^{*},\ y_2^{*}", side=RIGHT)

    x.add_process(["solver", "disc1", "disc2", "solver"], arrow=True)
    return x


def build_metamodel(api):
    """METAMODEL — a surrogate standing in for an expensive analysis.

    The yellow rectangle is a *metamodel* (surrogate): a cheap function fit
    offline to training data (typically from a DOE, see build_doe) that predicts
    the response of a costly analysis. Here an optimizer searches the surrogate
    `f-hat, g-hat` instead of calling the true analysis each iteration.
    """
    XDSM, OPT, METAMODEL, RIGHT = api["XDSM"], api["OPT"], api["METAMODEL"], api["RIGHT"]
    x = XDSM(use_sfmath=False)

    x.add_system("opt", OPT, (r"\text{Optimizer}",))
    x.add_system("surrogate", METAMODEL, (r"\text{Surrogate}",))

    x.add_input("opt", r"x^{(0)}")
    x.add_input("surrogate", r"\text{training data}")
    x.connect("opt", "surrogate", r"x")
    x.connect("surrogate", "opt", r"\hat{f},\ \hat{g}")
    x.add_output("opt", r"x^{*}", side=RIGHT)

    x.add_process(["opt", "surrogate", "opt"], arrow=True)
    return x


def build_group(api):
    """GROUP — a bundle of components exposed as one reusable sub-block.

    The green chamfered box is a *group*: several components (often coupled, with
    their own internal solver) collapsed into a single block when their internals
    are not the point. Here an optimizer drives an "Aerostructures" group that
    hides an internal aero-structures MDA behind one `x -> f, g` interface.
    """
    XDSM, OPT, GROUP, RIGHT = api["XDSM"], api["OPT"], api["GROUP"], api["RIGHT"]
    x = XDSM(use_sfmath=False)

    x.add_system("opt", OPT, (r"\text{Optimizer}",))
    x.add_system("group", GROUP, (r"\text{Aerostructures}", r"\text{(MDA group)}"))

    x.add_input("opt", r"x^{(0)}")
    x.connect("opt", "group", r"x")
    x.connect("group", "opt", r"f,\ g")
    x.add_output("opt", r"x^{*}", side=RIGHT)

    x.add_process(["opt", "group", "opt"], arrow=True)
    return x


def build_implicit(api):
    """IFUNC / IGROUP — implicit components that expose residuals to a solver.

    A `FUNC` is *explicit*: output = f(input). An *implicit* component instead
    defines a residual R(u) = 0 that an outer solver must drive to zero by
    choosing the state `u`. The salmon rectangle is an implicit function
    (`IFUNC`); the salmon chamfered box is an implicit subsystem (`IGROUP`). Both
    hand their residuals back up to the solver.
    """
    XDSM, SOLVER, IFUNC, IGROUP, RIGHT = (
        api["XDSM"],
        api["SOLVER"],
        api["IFUNC"],
        api["IGROUP"],
        api["RIGHT"],
    )
    x = XDSM(use_sfmath=False)

    x.add_system("solver", SOLVER, (r"\text{Newton}", r"\text{solver}"))
    x.add_system("comp", IFUNC, (r"\text{Implicit}", r"\text{component}"))
    x.add_system("sub", IGROUP, (r"\text{Implicit}", r"\text{subsystem}"))

    x.add_input("solver", r"u^{(0)}")
    x.connect("solver", "comp", r"u_1")
    x.connect("solver", "sub", r"u_2")
    x.connect("comp", "solver", r"\mathcal{R}_1(u_1)")
    x.connect("sub", "solver", r"\mathcal{R}_2(u_2)")
    x.add_output("solver", r"u^{*}", side=RIGHT)

    x.add_process(["solver", "comp", "sub", "solver"], arrow=True)
    return x


DIAGRAMS = [
    ("shape_optimization", build_optimization),
    ("shape_doe", build_doe),
    ("shape_bilevel", build_bilevel),
    ("shape_stack", build_stack),
    ("shape_solver", build_solver),
    ("shape_metamodel", build_metamodel),
    ("shape_group", build_group),
    ("shape_implicit", build_implicit),
]


# --------------------------------------------------------------------------- #
# Rendering: mirror generate_xdsm.py — write .tex/.tikz, run pdflatex with the
# output directory as cwd (robust on Windows), convert to PNG, then clean up.
# --------------------------------------------------------------------------- #
def _require_executable(name: str, purpose: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise MissingPrerequisiteError(
            f"Missing prerequisite: executable '{name}' is required for {purpose}."
        )
    return executable


def _cleanup(stem: Path) -> None:
    for suffix in (".aux", ".fdb_latexmk", ".fls", ".log", ".tex", ".tikz"):
        artifact = stem.with_suffix(suffix)
        if artifact.exists():
            artifact.unlink()


def _render_one(basename: str, builder) -> list[Path]:
    xdsm = builder(_pyxdsm_api())
    xdsm.write(basename, build=False, cleanup=True, outdir=str(OUTPUT_DIR))

    tex_path = OUTPUT_DIR / f"{basename}.tex"
    _require_executable("pdflatex", "pyXDSM PDF rendering")
    subprocess.run(
        ["pdflatex", "-halt-on-error", "-interaction=nonstopmode", tex_path.name],
        cwd=tex_path.parent,
        check=True,
    )

    written = [OUTPUT_DIR / f"{basename}.pdf"]
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is not None:
        png_prefix = OUTPUT_DIR / basename
        subprocess.run(
            [pdftoppm, "-png", "-r", "200", "-singlefile",
             str(written[0]), str(png_prefix)],
            check=True,
        )
        written.append(png_prefix.with_suffix(".png"))

    _cleanup(tex_path.with_suffix(""))
    return written


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        for basename, builder in DIAGRAMS:
            for path in _render_one(basename, builder):
                print(f"Wrote {path.relative_to(REPO_ROOT)}")
    except MissingPrerequisiteError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
