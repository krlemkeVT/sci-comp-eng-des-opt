"""The Sellar MDA - final, complete reference model.

This is where the in-class walkthrough (``steps/step_1`` ... ``steps/step_7``)
lands: the two coupled Sellar disciplines wrapped in a ``cycle`` subgroup with a
nonlinear solver, plus the objective and two constraints. It reproduces the
canonical OpenMDAO Sellar model
(https://openmdao.org/newdocs/versions/latest/basic_user_guide/multidisciplinary_optimization/sellar.html)
in plain numpy, using ``promotes`` to wire same-named variables and
``declare_partials(method='fd')`` for derivatives.

Running it converges the MDA at the default design point (z=[5, 2], x=1), prints
the results, and writes an N2 diagram to ``outputs/sellar_n2.html``.

To compare nonlinear solvers (fixed point / Aitken / Newton / Broyden) on this
same model, see ``steps/step_7_solver_compare.py``.

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_02_iterative_methods/sellar/sellar_mda.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import openmdao.api as om

OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


class SellarDis1(om.ExplicitComponent):
    """Discipline 1: ``y1 = z1**2 + z2 + x - 0.2 * y2``."""

    def setup(self):
        self.add_input("z", val=np.zeros(2))   # [z1, z2] shared design variables
        self.add_input("x", val=0.0)           # local design variable
        self.add_input("y2", val=1.0)          # coupling variable IN (from Discipline 2)
        self.add_output("y1", val=1.0)         # coupling variable OUT (to Discipline 2)

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
        self.add_input("y1", val=1.0)          # coupling variable IN (from Discipline 1)
        self.add_output("y2", val=1.0)         # coupling variable OUT (to Discipline 1)

    def setup_partials(self):
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs):
        z1 = inputs["z"][0]
        z2 = inputs["z"][1]
        y1 = inputs["y1"]
        # Guard the square root against a negative y1 during iteration.
        if y1.real < 0.0:
            y1 *= -1
        outputs["y2"] = y1**0.5 + z1 + z2


class SellarMDA(om.Group):
    """Sellar multidisciplinary analysis: coupled disciplines + objective + constraints."""

    def setup(self):
        # Coupled disciplines in their own subgroup, so the solver wraps only the
        # loop. promotes=['*'] lifts x, z, y1, y2 to this group's level; promotion
        # auto-connects d1.y1 -> d2.y1 and d2.y2 -> d1.y2 by name.
        cycle = self.add_subsystem("cycle", om.Group(), promotes=["*"])
        cycle.add_subsystem(
            "d1", SellarDis1(),
            promotes_inputs=["x", "z", "y2"], promotes_outputs=["y1"],
        )
        cycle.add_subsystem(
            "d2", SellarDis2(),
            promotes_inputs=["z", "y1"], promotes_outputs=["y2"],
        )
        cycle.nonlinear_solver = om.NonlinearBlockGS()

        self.set_input_defaults("x", val=1.0)
        self.set_input_defaults("z", val=np.array([5.0, 2.0]))

        # Objective and constraints as one-line ExplicitComponents (FUNC boxes).
        self.add_subsystem(
            "obj_cmp",
            om.ExecComp("obj = x**2 + z[1] + y1 + exp(-y2)", z=np.array([0.0, 0.0]), x=0.0),
            promotes=["x", "z", "y1", "y2", "obj"],
        )
        self.add_subsystem("con_cmp1", om.ExecComp("con1 = 3.16 - y1"), promotes=["con1", "y1"])
        self.add_subsystem("con_cmp2", om.ExecComp("con2 = y2 - 24.0"), promotes=["con2", "y2"])


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    prob = om.Problem(model=SellarMDA())
    prob.setup()

    # Default design point (change these to explore the analysis).
    prob.set_val("z", [5.0, 2.0])
    prob.set_val("x", 1.0)
    prob.run_model()

    print("Sellar MDA converged at z=[5, 2], x=1:")
    print(f"  y1   = {prob.get_val('y1')[0]:.4f}")
    print(f"  y2   = {prob.get_val('y2')[0]:.4f}")
    print(f"  obj  = {prob.get_val('obj')[0]:.4f}")
    print(f"  con1 = {prob.get_val('con1')[0]:.4f}")
    print(f"  con2 = {prob.get_val('con2')[0]:.4f}")

    n2_file = OUTPUT_DIR / "sellar_n2.html"
    om.n2(prob, outfile=str(n2_file), show_browser=False)
    print(f"\nWrote {n2_file}")


if __name__ == "__main__":
    main()
