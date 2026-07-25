"""Lesson 2: compare nonlinear solvers and derivative methods on the ASW loop.

Run from the repository root (with the ``aircraft-sizing`` environment active)::

    python lessons/lesson_02_iterative_methods/compare_solvers.py

It solves the identical ASW model with four nonlinear solvers, counts the
iterations and function/derivative evaluations each one costs, plots the residual
convergence, and finally contrasts analytic (JAX) total derivatives against a
finite-difference of the whole model. Outputs land in ``outputs/``.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import openmdao.api as om  # noqa: E402

# compute_totals prints an informational note about the solver; not relevant here.
import warnings  # noqa: E402

try:
    from openmdao.utils.om_warnings import OpenMDAOWarning

    warnings.filterwarnings("ignore", category=OpenMDAOWarning)
except Exception:  # pragma: no cover - depends on OpenMDAO internals
    pass

from aircraft_sizing.examples.ex_01_asw.methods.components import CallCounter  # noqa: E402
from aircraft_sizing.examples.ex_01_asw.methods.config import ASWSizingInputs, solve  # noqa: E402
from aircraft_sizing.examples.ex_01_asw.methods.group import build_asw_problem  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"

SOLVER_LABELS = {
    "nlbgs": "Fixed point (Gauss-Seidel)",
    "nlbgs_aitken": "Fixed point + Aitken",
    "newton": "Newton",
    "broyden": "Broyden",
}


def _call_summary(counter: CallCounter) -> tuple[int, int]:
    """Return (function evaluations, derivative evaluations) from a CallCounter."""
    function_evals = sum(
        n for (_, kind), n in counter.counts.items()
        if kind in ("compute", "apply_nonlinear", "solve_nonlinear")
    )
    derivative_evals = sum(
        n for (_, kind), n in counter.counts.items() if kind in ("partials", "linearize")
    )
    return function_evals, derivative_evals


def run_solver(solver: str, deriv: str, work_dir: Path) -> dict:
    """Solve once; return iterations, residual history, call counts, and TOGW."""
    inputs = ASWSizingInputs.baseline()
    counter = CallCounter()
    problem = build_asw_problem(
        inputs.params(), inputs.input_values(), solver=solver, deriv=deriv, counter=counter
    )
    sql = work_dir / f"cases_{solver}_{deriv}.sql"
    recorder = om.SqliteRecorder(str(sql))
    problem.model.nonlinear_solver.add_recorder(recorder)
    problem.model.nonlinear_solver.recording_options["record_abs_error"] = True

    with np.errstate(divide="ignore", invalid="ignore"):
        problem.run_model()
    problem.cleanup()

    cases = om.CaseReader(str(sql)).get_cases("root.nonlinear_solver", recurse=False)
    residuals = [float(case.abs_err) for case in cases]
    function_evals, derivative_evals = _call_summary(counter)
    return {
        "solver": solver,
        "deriv": deriv,
        "iterations": int(problem.model.nonlinear_solver._iter_count),
        "residuals": residuals,
        "function_evals": function_evals,
        "derivative_evals": derivative_evals,
        "togw": float(problem.get_val("sizing.takeoff_gross_weight")[0]),
    }


def compare_derivatives() -> list[dict]:
    """Analytic (JAX) total derivatives vs a central finite-difference of solve()."""
    inputs = ASWSizingInputs.baseline()
    problem = build_asw_problem(inputs.params(), inputs.input_values(), solver="nlbgs")
    problem.run_model()
    wrt = ["aero.wing_aspect_ratio", "prop.tsfc_cruise_per_hr", "mission.range_ft"]
    analytic = problem.compute_totals(of=["sizing.takeoff_gross_weight"], wrt=wrt)

    # Central FD of the whole solve, in the model's input units.
    specs = [
        ("aero.wing_aspect_ratio", "wing_aspect_ratio", 7.0, 1e-3, 1.0),
        ("prop.tsfc_cruise_per_hr", "cruise_thrust_specific_fuel_consumption_lb_per_hr_per_lb", 0.5, 1e-5, 1.0),
        ("mission.range_ft", "cruise_range_one_way_nm", 1500.0, 1e-2, 6076.0),
    ]
    rows = []
    for path, field, base_value, step, unit_per_input in specs:
        high = solve(inputs.with_value(field, base_value + step)).final_takeoff_gross_weight_lb
        low = solve(inputs.with_value(field, base_value - step)).final_takeoff_gross_weight_lb
        fd = (high - low) / (2.0 * step) / unit_per_input
        exact = float(analytic["sizing.takeoff_gross_weight", path][0, 0])
        rows.append(
            {
                "input": path,
                "analytic": exact,
                "finite_difference": fd,
                "rel_diff": abs(exact - fd) / abs(exact),
            }
        )
    return rows


def plot_convergence(results: list[dict], outfile: Path) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    for result in results:
        residuals = [max(value, 1e-12) for value in result["residuals"]]
        axis.semilogy(
            range(len(residuals)),
            residuals,
            marker="o",
            label=f"{SOLVER_LABELS[result['solver']]} ({result['iterations']} it)",
        )
    axis.set_title("ASW sizing-loop residual convergence (analytic JAX gradients)")
    axis.set_xlabel("Solver iteration")
    axis.set_ylabel("Residual norm |R(W_TO)|")
    axis.grid(True, which="both", alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(outfile, dpi=140)
    plt.close(figure)


def write_report(solver_rows: list[dict], fd_newton: dict, derivative_rows: list[dict], outfile: Path) -> None:
    lines = ["# Lesson 2 — solver & derivative comparison (generated)", ""]
    lines.append("## Nonlinear solvers (analytic JAX gradients)")
    lines.append("")
    lines.append("| Solver | Iterations | Function evals | Derivative evals | Converged TOGW [lb] |")
    lines.append("|---|---|---|---|---|")
    for row in solver_rows:
        lines.append(
            f"| {SOLVER_LABELS[row['solver']]} | {row['iterations']} | {row['function_evals']} | "
            f"{row['derivative_evals']} | {row['togw']:.2f} |"
        )
    lines.append("")
    newton_jax = next(r for r in solver_rows if r["solver"] == "newton")
    lines.append("## Newton: analytic JAX Jacobian vs finite-difference partials")
    lines.append("")
    lines.append("| Derivative source | Iterations | Function evals | Derivative evals | Converged TOGW [lb] |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        f"| JAX (analytic) | {newton_jax['iterations']} | {newton_jax['function_evals']} | "
        f"{newton_jax['derivative_evals']} | {newton_jax['togw']:.2f} |"
    )
    lines.append(
        f"| Finite difference | {fd_newton['iterations']} | {fd_newton['function_evals']} | "
        f"{fd_newton['derivative_evals']} | {fd_newton['togw']:.2f} |"
    )
    lines.append("")
    lines.append("## Total derivative dW_TO/d(input): analytic JAX vs finite difference")
    lines.append("")
    lines.append("| Input | Analytic (JAX) | Finite difference | Relative difference |")
    lines.append("|---|---|---|---|")
    for row in derivative_rows:
        lines.append(
            f"| `{row['input']}` | {row['analytic']:.6e} | {row['finite_difference']:.6e} | {row['rel_diff']:.2e} |"
        )
    lines.append("")
    outfile.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        solver_rows = [run_solver(solver, "jax", work_dir) for solver in SOLVER_LABELS]
        fd_newton = run_solver("newton", "fd", work_dir)

    derivative_rows = compare_derivatives()
    plot_convergence(solver_rows, OUTPUT_DIR / "convergence.png")
    write_report(solver_rows, fd_newton, derivative_rows, OUTPUT_DIR / "solver_comparison.md")

    print("Nonlinear solvers (analytic JAX gradients):")
    for row in solver_rows:
        print(
            f"  {SOLVER_LABELS[row['solver']]:26s} iters={row['iterations']:3d}  "
            f"f-evals={row['function_evals']:4d}  d-evals={row['derivative_evals']:3d}  "
            f"TOGW={row['togw']:.2f}"
        )
    print("\nNewton, JAX vs finite-difference partials:")
    newton_jax = next(r for r in solver_rows if r["solver"] == "newton")
    print(f"  JAX  iters={newton_jax['iterations']} f-evals={newton_jax['function_evals']} d-evals={newton_jax['derivative_evals']}")
    print(f"  FD   iters={fd_newton['iterations']} f-evals={fd_newton['function_evals']} d-evals={fd_newton['derivative_evals']}")
    print("\nTotal derivative dW_TO/d(input), analytic vs FD:")
    for row in derivative_rows:
        print(f"  {row['input']:26s} analytic={row['analytic']: .4e}  fd={row['finite_difference']: .4e}  rel={row['rel_diff']:.1e}")
    print(f"\nWrote {(OUTPUT_DIR / 'convergence.png').relative_to(REPO_ROOT)} and solver_comparison.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
