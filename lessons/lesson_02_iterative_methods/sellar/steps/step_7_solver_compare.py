"""Sellar walkthrough - Step 7: same MDA, four nonlinear solvers.

This mirrors, on the Sellar loop, exactly what ``asw/compare_solvers.py`` does on
the ASW loop: solve the *identical* coupled model with fixed point (Gauss-Seidel),
Aitken-accelerated fixed point, Newton, and Broyden, and count the iterations each
one takes. All four land on the same y1/y2 - the answer is a property of the
model, not the solver - but the number of sweeps (and what each sweep costs)
differs. Newton additionally needs a linear solver on the group to take its step.

Writes a residual-convergence plot to ``sellar/outputs/sellar_convergence.png``.
The per-run recorder databases are temporary and are not kept.

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_02_iterative_methods/sellar/steps/step_7_solver_compare.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import openmdao.api as om  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"

SOLVER_LABELS = {
    "nlbgs": "Fixed point (Gauss-Seidel)",
    "nlbgs_aitken": "Fixed point + Aitken",
    "newton": "Newton",
    "broyden": "Broyden",
}


class SellarDis1(om.ExplicitComponent):
    """Discipline 1: ``y1 = z1**2 + z2 + x - 0.2 * y2``."""

    def setup(self):
        self.add_input("z", val=np.zeros(2))
        self.add_input("x", val=0.0)
        self.add_input("y2", val=1.0)
        self.add_output("y1", val=1.0)

    def setup_partials(self):
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs):
        z1 = inputs["z"][0]
        z2 = inputs["z"][1]
        x = inputs["x"]
        y2 = inputs["y2"]
        outputs["y1"] = z1**2 + z2 + x - 0.2 * y2


class SellarDis2(om.ExplicitComponent):
    """Discipline 2: ``y2 = sqrt(y1) + z1 + z2``."""

    def setup(self):
        self.add_input("z", val=np.zeros(2))
        self.add_input("y1", val=1.0)
        self.add_output("y2", val=1.0)

    def setup_partials(self):
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs):
        z1 = inputs["z"][0]
        z2 = inputs["z"][1]
        y1 = inputs["y1"]
        if y1.real < 0.0:
            y1 *= -1
        outputs["y2"] = y1**0.5 + z1 + z2


def make_nonlinear_solver(kind: str):
    """Build one of the four nonlinear solvers with matched tolerances."""
    if kind == "nlbgs":
        solver = om.NonlinearBlockGS()
    elif kind == "nlbgs_aitken":
        solver = om.NonlinearBlockGS()
        solver.options["use_aitken"] = True
    elif kind == "newton":
        solver = om.NewtonSolver(solve_subsystems=False)
    elif kind == "broyden":
        solver = om.BroydenSolver()
        solver.options["state_vars"] = ["y1", "y2"]   # the coupling variables
    else:  # pragma: no cover
        raise ValueError(f"unknown solver {kind!r}")

    solver.options["maxiter"] = 50
    solver.options["atol"] = 1e-10
    solver.options["rtol"] = 1e-12
    solver.options["iprint"] = 0
    return solver


class SellarMDA(om.Group):
    """Sellar MDA whose loop solver is chosen by the ``solver`` option."""

    def initialize(self):
        self.options.declare("solver", default="nlbgs", values=tuple(SOLVER_LABELS))

    def setup(self):
        kind = self.options["solver"]
        cycle = self.add_subsystem("cycle", om.Group(), promotes=["*"])
        cycle.add_subsystem(
            "d1", SellarDis1(),
            promotes_inputs=["x", "z", "y2"], promotes_outputs=["y1"],
        )
        cycle.add_subsystem(
            "d2", SellarDis2(),
            promotes_inputs=["z", "y1"], promotes_outputs=["y2"],
        )
        cycle.nonlinear_solver = make_nonlinear_solver(kind)
        if kind in ("newton", "broyden"):
            cycle.linear_solver = om.DirectSolver()   # supplies the linearized step

        self.set_input_defaults("x", val=1.0)
        self.set_input_defaults("z", val=np.array([5.0, 2.0]))

        self.add_subsystem(
            "obj_cmp",
            om.ExecComp("obj = x**2 + z[1] + y1 + exp(-y2)", z=np.array([0.0, 0.0]), x=0.0),
            promotes=["x", "z", "y1", "y2", "obj"],
        )
        self.add_subsystem("con_cmp1", om.ExecComp("con1 = 3.16 - y1"), promotes=["con1", "y1"])
        self.add_subsystem("con_cmp2", om.ExecComp("con2 = y2 - 24.0"), promotes=["con2", "y2"])


def run_solver(kind: str, work_dir: Path) -> dict:
    """Solve once; return iteration count, residual history, and converged y1/y2."""
    prob = om.Problem(model=SellarMDA(solver=kind), reports=False)
    prob.setup()

    solver = prob.model.cycle.nonlinear_solver
    sql = work_dir / f"cases_{kind}.sql"
    solver.add_recorder(om.SqliteRecorder(str(sql)))
    solver.recording_options["record_abs_error"] = True

    with np.errstate(divide="ignore", invalid="ignore"):
        prob.run_model()
    prob.cleanup()

    cases = om.CaseReader(str(sql)).get_cases("root.cycle.nonlinear_solver", recurse=False)
    residuals = [float(case.abs_err) for case in cases]
    return {
        "kind": kind,
        "iterations": int(solver._iter_count),
        "residuals": residuals,
        "y1": float(prob.get_val("y1")[0]),
        "y2": float(prob.get_val("y2")[0]),
    }


def plot_convergence(results: list[dict], outfile: Path) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    for result in results:
        residuals = [max(value, 1e-12) for value in result["residuals"]]
        axis.semilogy(
            range(len(residuals)),
            residuals,
            marker="o",
            label=f"{SOLVER_LABELS[result['kind']]} ({result['iterations']} it)",
        )
    axis.set_title("Sellar MDA residual convergence (finite-difference partials)")
    axis.set_xlabel("Solver iteration")
    axis.set_ylabel("Residual norm")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(outfile, dpi=140)
    plt.close(figure)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        results = [run_solver(kind, Path(tmp)) for kind in SOLVER_LABELS]

    plot_convergence(results, OUTPUT_DIR / "sellar_convergence.png")

    print("Nonlinear solvers on the Sellar MDA (finite-difference partials):")
    for result in results:
        print(
            f"  {SOLVER_LABELS[result['kind']]:26s} iters={result['iterations']:3d}  "
            f"y1={result['y1']:.4f}  y2={result['y2']:.4f}"
        )
    print(f"\nWrote {OUTPUT_DIR / 'sellar_convergence.png'}")


if __name__ == "__main__":
    main()
