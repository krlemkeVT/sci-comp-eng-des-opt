"""Sellar walkthrough - Step 1: Discipline 1 as an ExplicitComponent.

Discipline 1 of the Sellar problem computes the coupling variable ``y1``::

    y1 = z1**2 + z2 + x - 0.2 * y2

We run it on its own to make one point up front: a single ``ExplicitComponent``
is already a complete, runnable OpenMDAO model. Note that ``y2`` is an *input*
here even though Discipline 2 will eventually produce it - a component never knows
(or cares) where its inputs come from. That is what makes disciplines composable.

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_02_iterative_methods/sellar/steps/step_1_discipline1.py
"""

from __future__ import annotations

import numpy as np
import openmdao.api as om


class SellarDis1(om.ExplicitComponent):
    """Discipline 1: ``y1 = z1**2 + z2 + x - 0.2 * y2``."""

    def setup(self):
        # Every variable is declared by name with a value/shape, because the
        # framework allocates the input/output vectors for us.
        self.add_input("z", val=np.zeros(2))   # [z1, z2] shared (global) design variables
        self.add_input("x", val=0.0)           # local design variable
        self.add_input("y2", val=1.0)          # coupling variable IN (from Discipline 2)
        self.add_output("y1", val=1.0)         # coupling variable OUT (to Discipline 2)

    def setup_partials(self):
        # Finite-difference every partial. Cheap to write and fine for teaching;
        # we contrast this with analytic (JAX) derivatives at the end of the lesson.
        self.declare_partials("*", "*", method="fd")

    def compute(self, inputs, outputs):
        z1 = inputs["z"][0]
        z2 = inputs["z"][1]
        x = inputs["x"]
        y2 = inputs["y2"]
        outputs["y1"] = z1**2 + z2 + x - 0.2 * y2


def main():
    prob = om.Problem()
    prob.model.add_subsystem("d1", SellarDis1(), promotes=["*"])
    prob.setup()

    # z and x are the design point; y2 is a guess (nothing is being solved yet).
    prob.set_val("z", [5.0, 2.0])
    prob.set_val("x", 1.0)
    prob.set_val("y2", 1.0)
    prob.run_model()

    print(f"y1 = {prob.get_val('y1')[0]:.4f}   (expected 27.8000 for z=[5,2], x=1, y2=1)")


if __name__ == "__main__":
    main()
