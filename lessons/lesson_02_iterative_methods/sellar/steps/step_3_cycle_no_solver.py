"""Sellar walkthrough - Step 3: wire the cycle, run it WITHOUT a solver.

We add both disciplines to a group and connect them:

    d1.y1 -> d2.y1   (feed-forward: y1 flows to the later discipline)
    d2.y2 -> d1.y2   (feedback:     y2 flows back to the earlier discipline)

The feedback edge is the whole story. A group, by default, runs each subsystem
**exactly once, in the order added**. So d1 runs (with the initial y2), then d2
runs (with d1's fresh y1) - and we stop. The two disciplines are *not* mutually
consistent: if you feed d2's y2 back into d1, you get a different y1. That gap is
the coupled loop that Lesson 1's DSM flagged as the one edge below the diagonal.

OpenMDAO does not raise an error here - it quietly runs the single pass and hands
back the inconsistent values. The culprit is invisible in the numbers but obvious
in the picture: the N2 in Step 5 shows a connection running BELOW the diagonal (the
feedback edge) with no solver looped around it. Giving that loop a solver is Step 4.

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_02_iterative_methods/sellar/steps/step_3_cycle_no_solver.py
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

    # Shared design inputs (z, x) are promoted so one value feeds both disciplines.
    model.add_subsystem("d1", SellarDis1(), promotes_inputs=["z", "x"])
    model.add_subsystem("d2", SellarDis2(), promotes_inputs=["z"])

    # Internal coupling wired explicitly so the data flow is visible.
    model.connect("d1.y1", "d2.y1")   # feed-forward
    model.connect("d2.y2", "d1.y2")   # feedback - the loop

    model.set_input_defaults("x", val=1.0)
    model.set_input_defaults("z", val=np.array([5.0, 2.0]))

    prob.setup()
    prob.run_model()   # no nonlinear solver -> a single pass, d1 then d2

    y1 = prob.get_val("d1.y1")[0]
    y2 = prob.get_val("d2.y2")[0]
    print(f"After one pass:      y1 = {y1:.4f},  y2 = {y2:.4f}")

    # Feed that y2 back into Discipline 1 by hand: the y1 it implies is different.
    y1_recheck = 5.0**2 + 2.0 + 1.0 - 0.2 * y2
    print(f"Re-evaluating d1 with that y2 gives  y1 = {y1_recheck:.4f}")
    print(f"  -> mismatch of {abs(y1 - y1_recheck):.4f}: the feedback loop is NOT converged.")


if __name__ == "__main__":
    main()
