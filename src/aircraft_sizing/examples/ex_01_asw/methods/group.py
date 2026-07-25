"""The ASW multidisciplinary group and a problem-builder shared everywhere.

``ASWSizingGroup`` assembles the five disciplines and wires the couplings.  The
data flow is feed-forward -- ``aero`` / ``prop`` -> ``mission`` -> ``sizing`` --
except for the single feedback loop ``sizing <-> struct`` through the takeoff
gross weight.  That one loop is what the nonlinear solver must converge, and it is
the whole subject of Lesson 2.

``build_asw_problem`` is the single entry point used by the solver, the Streamlit
app, the tests, and both lessons; it lets the caller pick the nonlinear solver and
the derivative mode (analytic JAX vs finite difference).
"""

from __future__ import annotations

import openmdao.api as om

from .components import Aerodynamics, MissionFuel, Propulsion, Sizing, Structures


class ASWSizingGroup(om.Group):
    """Five ASW disciplines wired into one fixed-point sizing loop."""

    def initialize(self) -> None:
        self.options.declare("params", types=dict, default=None, recordable=False)
        self.options.declare("counter", default=None, recordable=False)
        self.options.declare("deriv", default="jax", values=("jax", "fd"))

    def setup(self) -> None:
        p = self.options["params"] or {}
        counter = self.options["counter"]
        deriv = self.options["deriv"]

        self.add_subsystem(
            "aero",
            Aerodynamics(
                counter=counter, deriv=deriv,
                k_ld=p.get("k_ld", 14.0),
                cruise_ld_factor=p.get("cruise_ld_factor", 0.866),
            ),
        )
        self.add_subsystem("prop", Propulsion(counter=counter, deriv=deriv))
        self.add_subsystem(
            "mission",
            MissionFuel(
                counter=counter, deriv=deriv,
                warmup=p.get("warmup", 0.970),
                climb=p.get("climb", 0.985),
                landing=p.get("landing", 0.995),
                reserve=p.get("reserve", 0.05),
                trapped=p.get("trapped", 0.01),
            ),
        )
        self.add_subsystem(
            "struct",
            Structures(
                counter=counter, deriv=deriv,
                coefficient=p.get("coefficient", 0.93),
                exponent=p.get("exponent", -0.07),
                material_factor=p.get("material_factor", 1.0),
            ),
        )
        self.add_subsystem("sizing", Sizing(counter=counter, deriv=deriv))

        # Feed-forward couplings.
        self.connect("aero.cruise_lift_to_drag", "mission.cruise_lift_to_drag")
        self.connect("aero.loiter_lift_to_drag", "mission.loiter_lift_to_drag")
        self.connect("prop.cruise_speed", "mission.cruise_speed")
        self.connect("prop.sfc_cruise", "mission.sfc_cruise")
        self.connect("prop.sfc_loiter", "mission.sfc_loiter")
        self.connect("mission.fuel_weight_fraction", "sizing.fuel_weight_fraction")
        self.connect("struct.empty_weight_fraction", "sizing.empty_weight_fraction")
        # The one feedback edge that makes this an implicit sizing problem.
        self.connect("sizing.takeoff_gross_weight", "struct.takeoff_gross_weight")


#: Nonlinear-solver keys accepted by :func:`build_asw_problem`.
SOLVER_CHOICES = ("nlbgs", "nlbgs_aitken", "newton", "broyden")


def make_nonlinear_solver(kind: str, *, maxiter: int = 200, iprint: int = 0):
    """Build one of the nonlinear solvers compared in Lesson 2."""
    if kind not in SOLVER_CHOICES:
        raise ValueError(f"solver must be one of {SOLVER_CHOICES}; got {kind!r}.")

    if kind in ("nlbgs", "nlbgs_aitken"):
        solver = om.NonlinearBlockGS()
        solver.options["use_aitken"] = kind == "nlbgs_aitken"
    elif kind == "newton":
        solver = om.NewtonSolver(solve_subsystems=False)
        # Enforce the W_TO lower bound so a Newton overshoot cannot make
        # We/WTO = a*WTO^b evaluate a negative base (NaN).
        solver.linesearch = om.BoundsEnforceLS()
    else:  # broyden
        solver = om.BroydenSolver()
        # Broyden works on the single implicit state W_TO (the rest of the model is
        # just re-evaluated to form the residual). Left to default it treats every
        # explicit output as a state, whose wildly different scales (fractions ~0.4
        # vs W_TO ~5e4) make the approximate Jacobian overshoot past the W_TO bound.
        solver.options["state_vars"] = ["sizing.takeoff_gross_weight"]
        solver.linesearch = om.BoundsEnforceLS()

    solver.options["maxiter"] = maxiter
    solver.options["atol"] = 1e-10
    solver.options["rtol"] = 1e-12
    solver.options["iprint"] = iprint
    return solver


def build_asw_problem(
    params: dict,
    input_values: dict,
    *,
    solver: str = "nlbgs",
    deriv: str = "jax",
    counter=None,
    initial_guess: float | None = None,
    iprint: int = 0,
) -> om.Problem:
    """Return a set-up ``om.Problem`` for the ASW sizing group.

    ``params`` holds the discipline constants (k_ld, material_factor, ...);
    ``input_values`` holds the top-level input values keyed by full path
    (e.g. ``"aero.wing_aspect_ratio"``).
    """
    # reports=False keeps OpenMDAO from writing a per-problem reports directory on
    # every solve (the app and sweeps build many problems).
    prob = om.Problem(reports=False)
    prob.model = ASWSizingGroup(params=params, counter=counter, deriv=deriv)
    prob.model.nonlinear_solver = make_nonlinear_solver(solver, iprint=iprint)
    prob.model.linear_solver = om.DirectSolver()

    prob.setup(force_alloc_complex=False)

    for path, value in input_values.items():
        prob.set_val(path, value)
    if initial_guess is not None:
        prob.set_val("sizing.takeoff_gross_weight", initial_guess)

    return prob
