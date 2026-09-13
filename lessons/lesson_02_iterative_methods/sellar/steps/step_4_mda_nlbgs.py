"""Sellar walkthrough - Step 4: add the MDA solver -> the loop converges.

This is the one-line change that turns Step 3's single pass into a real
**multidisciplinary analysis (MDA)**::

    model.nonlinear_solver = om.NonlinearBlockGS()

Nonlinear Block Gauss-Seidel = evaluate d1, pass y1 to d2, pass y2 back to d1,
and repeat until the values stop changing. That is exactly the fixed-point idea
behind Raymer's ASW hand-iteration - only now there are *two* coupling variables
(y1, y2) being driven to consistency instead of one implicit scalar. With
``iprint=2`` you can watch the residual fall on every sweep.

This converged model IS the Sellar MDA - the target of today's build.

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_02_iterative_methods/sellar/steps/step_4_mda_nlbgs.py
"""

from __future__ import annotations

import numpy as np
import openmdao.api as om


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


def main():
    prob = om.Problem()
    model = prob.model

    model.add_subsystem("d1", SellarDis1(), promotes_inputs=["z", "x"])
    model.add_subsystem("d2", SellarDis2(), promotes_inputs=["z"])
    model.connect("d1.y1", "d2.y1")
    model.connect("d2.y2", "d1.y2")
    model.set_input_defaults("x", val=1.0)
    model.set_input_defaults("z", val=np.array([5.0, 2.0]))

    # THE change from Step 3: give the coupled group an iterative nonlinear solver.
    model.nonlinear_solver = om.NonlinearBlockGS()
    model.nonlinear_solver.options["iprint"] = 2   # print the residual each sweep

    prob.setup()
    prob.run_model()

    y1 = prob.get_val("d1.y1")[0]
    y2 = prob.get_val("d2.y2")[0]
    print(f"\nConverged MDA:  y1 = {y1:.4f},  y2 = {y2:.4f}")
    print("  (expected y1 ~ 25.59, y2 ~ 12.06 for z=[5,2], x=1)")


if __name__ == "__main__":
    main()
