"""Sellar walkthrough - Step 2: add Discipline 2.

Discipline 2 computes the other coupling variable ``y2``::

    y2 = sqrt(y1) + z1 + z2

``y1`` is Discipline 2's *input* and Discipline 1's *output*: the shared **name**
is exactly how the two will be connected in the next step. Note the guard around
the square root - during iteration a stray negative ``y1`` would otherwise produce
a NaN and kill the solve (the same reason the ASW loop needed bounds).

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_02_iterative_methods/sellar/steps/step_2_discipline2.py
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
        self.add_input("y1", val=1.0)          # coupling variable IN (from Discipline 1)
        self.add_output("y2", val=1.0)         # coupling variable OUT (to Discipline 1)

    def setup_partials(self):
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs):
        z1 = inputs["z"][0]
        z2 = inputs["z"][1]
        y1 = inputs["y1"]
        # Guard the square root: a negative y1 mid-iteration would give a NaN.
        if y1.real < 0.0:
            y1 *= -1
        outputs["y2"] = y1**0.5 + z1 + z2


def main():
    prob = om.Problem()
    prob.model.add_subsystem("d2", SellarDis2(), promotes=["*"])
    prob.setup()

    prob.set_val("z", [5.0, 2.0])
    prob.set_val("y1", 1.0)
    prob.run_model()

    print(f"y2 = {prob.get_val('y2')[0]:.4f}   (expected 8.0000 for z=[5,2], y1=1)")


if __name__ == "__main__":
    main()
