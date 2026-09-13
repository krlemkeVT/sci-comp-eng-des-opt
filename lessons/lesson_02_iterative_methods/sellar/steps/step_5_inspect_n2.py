"""Sellar walkthrough - Step 5: inspect the live model (N2 + variable lists).

Same converged MDA as Step 4, now interrogated with OpenMDAO's built-in tools:

* ``om.n2(prob, ...)`` writes an interactive N2 (the same DSM you drew by hand in
  Lesson 1, generated straight from the live model). Open the HTML and find the
  ``y2`` connection running BELOW the diagonal - that is the feedback edge, and
  OpenMDAO marks the solver loop that wraps it.
* ``list_inputs`` / ``list_outputs`` dump every variable the framework allocated,
  with promoted names - useful while building or debugging.

Writes ``sellar/outputs/sellar_n2.html``.

Run from the repository root (with the ``eng-des-opt-course`` environment active)::

    python lessons/lesson_02_iterative_methods/sellar/steps/step_5_inspect_n2.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import openmdao.api as om

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    prob = om.Problem()
    model = prob.model
    model.add_subsystem("d1", SellarDis1(), promotes_inputs=["z", "x"])
    model.add_subsystem("d2", SellarDis2(), promotes_inputs=["z"])
    model.connect("d1.y1", "d2.y1")
    model.connect("d2.y2", "d1.y2")
    model.set_input_defaults("x", val=1.0)
    model.set_input_defaults("z", val=np.array([5.0, 2.0]))
    model.nonlinear_solver = om.NonlinearBlockGS()

    prob.setup()
    prob.run_model()

    n2_file = OUTPUT_DIR / "sellar_n2.html"
    om.n2(prob, outfile=str(n2_file), show_browser=False)

    print("Inputs:")
    prob.model.list_inputs(prom_name=True)
    print("\nOutputs:")
    prob.model.list_outputs(prom_name=True)
    print(f"\nWrote {n2_file}")


if __name__ == "__main__":
    main()
